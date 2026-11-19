import Foundation
import SwiftUI
import AppKit

struct FirmwareInfo: Codable, Equatable {
    var model: String = "Mi Box"
    var product: String = ""
    var android_release: String = "?"
    var sdk: String = "?"
    var build_id: String = ""
    var security_patch: String = ""
    var kernel: String = ""
    var arch_label: String = "unknown"
    var abis: [String] = []
    var free_storage_mb: Int?
    var free_ram_mb: Int?
    var hdmi_cec_enabled: Bool = false
    var hdmi_auto_device_off: Bool?
    var sleep_timeout_ms: Int?
    var tv_wake_ready: Bool = false
    var hid_drivers: [String] = []
    var has_magicmouse_driver: Bool = false
    var matvt_active: Bool = false
    var aerialviews_active: Bool = false
    var plain_summary: String = ""
}

struct CatalogAppInfo: Codable, Identifiable, Equatable {
    var key: String
    var title: String
    var package: String
    var detail: String
    var version: String?
    var asset: String
    var download_url: String
    var installed: Bool
    var simple_default: Bool
    var can_launch: Bool
    var id: String { key }
}

struct BloatPackageInfo: Codable, Identifiable, Equatable {
    var package: String
    var title: String
    var category: String
    var detail: String
    var `default`: Bool
    var danger: Bool
    var disabled: Bool
    var id: String { package }
}

struct ProgressInfo: Codable, Equatable {
    var step: Int = 0
    var total: Int = 5
    var label: String = "Ready"
}

struct EngineStatus: Codable, Equatable {
    var version: String = "2.1.0"
    var commit: String = "local"
    var lan_ip: String = "127.0.0.1"
    var connected: Bool = false
    var serial: String?
    var busy: Bool = false
    var progress: ProgressInfo = ProgressInfo()
    var logs: [String] = []
    var firmware: FirmwareInfo?
    var apps: [CatalogAppInfo] = []
    var bloat: [BloatPackageInfo] = []
}

enum UpdateState: Equatable {
    case idle
    case checking
    case upToDate(String)
    case available(sha: String, message: String)
    case failed(String)
}

@MainActor
final class AppModel: ObservableObject {
    static let shared = AppModel()

    @Published var status = EngineStatus()
    @Published var uiMode: String = "simple" // "simple" (75) or "advanced" (35)
    @Published var notice: String?
    @Published var manualIP: String = "192.168.0.117"
    @Published var update: UpdateState = .idle
    @Published var serverPort: Int = 8765

    private var serverProcess: Process?
    private var pollTask: Task<Void, Never>?

    var appVersion: String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "2.1.0"
    }

    var buildCommit: String {
        let raw = Bundle.main.infoDictionary?["MoBoxBuildCommit"] as? String ?? "local"
        return String(raw.prefix(7))
    }

    var phoneWebURL: String {
        "http://\(status.lan_ip):\(serverPort)"
    }

    private var apiBase: String {
        "http://127.0.0.1:\(serverPort)"
    }

    func startBackendIfNeeded() {
        if serverProcess?.isRunning == true { return }
        let resURL = Bundle.main.resourceURL
        let bundledRoot = resURL?.appendingPathComponent("engine")
        let devRoot = URL(fileURLWithPath: "/Users/Morad/C3PO/Tools/mibox-fixer")
        let engineRoot: URL
        if let bundledRoot, FileManager.default.fileExists(atPath: bundledRoot.appendingPathComponent("fixer/web.py").path) {
            engineRoot = bundledRoot
        } else {
            engineRoot = devRoot
        }

        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        proc.currentDirectoryURL = engineRoot
        proc.arguments = ["-m", "fixer.web", "--port", "\(serverPort)"]
        var env = ProcessInfo.processInfo.environment
        let extraPath = "/opt/homebrew/bin:/usr/local/bin:/usr/sbin:/sbin:" + (env["PATH"] ?? "/usr/bin:/bin")
        env["PATH"] = extraPath
        env["MOBOX_BUILD_COMMIT"] = Bundle.main.infoDictionary?["MoBoxBuildCommit"] as? String ?? "local"
        proc.environment = env
        proc.standardOutput = Pipe()
        proc.standardError = Pipe()
        do {
            try proc.run()
            self.serverProcess = proc
        } catch {
            self.notice = "Could not start local MoBox engine: \(error.localizedDescription)"
        }
    }

    func stopBackend() {
        pollTask?.cancel()
        if let proc = serverProcess, proc.isRunning {
            proc.terminate()
        }
        serverProcess = nil
    }

    func refresh(forceScan: Bool = false) async {
        startBackendIfNeeded()
        let urlStr = "\(apiBase)/api/status" + (forceScan ? "?scan=1" : "")
        guard let url = URL(string: urlStr) else { return }
        for attempt in 0..<4 {
            do {
                let (data, _) = try await URLSession.shared.data(from: url)
                let decoded = try JSONDecoder().decode(EngineStatus.self, from: data)
                self.status = decoded
                if let s = decoded.serial, let ip = s.split(separator: ":").first {
                    self.manualIP = String(ip)
                }
                return
            } catch {
                if attempt < 3 {
                    try? await Task.sleep(nanoseconds: 450_000_000)
                }
            }
        }
    }

    func connectManual() async {
        let host = manualIP.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !host.isEmpty, let url = URL(string: "\(apiBase)/api/connect") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONSerialization.data(withJSONObject: ["host": host])
        do {
            let (data, _) = try await URLSession.shared.data(for: req)
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                if (json["ok"] as? Bool) == true {
                    self.notice = "Connected to \(host)"
                    await refresh(forceScan: false)
                } else {
                    self.notice = (json["error"] as? String) ?? "Could not connect to \(host)"
                }
            }
        } catch {
            self.notice = "Connection failed: \(error.localizedDescription)"
        }
    }

    func runSimpleSetup() async {
        guard let url = URL(string: "\(apiBase)/api/simple-setup") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        _ = try? await URLSession.shared.data(for: req)
        self.notice = "Running MoBox All-in-One Setup…"
        startProgressPolling()
    }

    func performAction(_ kind: String, extra: [String: Any] = [:]) async {
        guard let url = URL(string: "\(apiBase)/api/action") else { return }
        var body: [String: Any] = ["kind": kind]
        for (k, v) in extra { body[k] = v }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONSerialization.data(withJSONObject: body)
        do {
            let (data, _) = try await URLSession.shared.data(for: req)
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                if let msg = json["message"] as? String {
                    self.notice = msg
                } else if let err = json["error"] as? String {
                    self.notice = err
                }
            }
            if kind == "install_app" || kind == "debloat_safe" {
                startProgressPolling()
            } else {
                await refresh(forceScan: false)
            }
        } catch {
            self.notice = "Action failed: \(error.localizedDescription)"
        }
    }

    private func startProgressPolling() {
        pollTask?.cancel()
        pollTask = Task {
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                guard let url = URL(string: "\(apiBase)/api/progress"),
                      let (data, _) = try? await URLSession.shared.data(from: url),
                      let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                    break
                }
                let busy = (json["busy"] as? Bool) ?? false
                let step = (json["step"] as? Int) ?? 0
                let total = (json["total"] as? Int) ?? 5
                let label = (json["label"] as? String) ?? ""
                let logs = (json["logs"] as? [String]) ?? []
                self.status.busy = busy
                self.status.progress = ProgressInfo(step: step, total: total, label: label)
                self.status.logs = logs
                if !busy {
                    await refresh(forceScan: false)
                    break
                }
            }
        }
    }

    func checkForUpdate() async {
        update = .checking
        guard let url = URL(string: "https://api.github.com/repos/aghamorad/mibox-fixer/commits/main") else {
            update = .failed("Bad URL")
            return
        }
        var req = URLRequest(url: url)
        req.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
        req.setValue("MoBox-Mac", forHTTPHeaderField: "User-Agent")
        do {
            let (data, _) = try await URLSession.shared.data(for: req)
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
               let sha = json["sha"] as? String {
                let shortRemote = String(sha.prefix(7))
                let commitDict = json["commit"] as? [String: Any]
                let msg = ((commitDict?["message"] as? String) ?? "").components(separatedBy: "\n").first ?? ""
                if buildCommit != "unknown" && buildCommit != "local" && shortRemote != buildCommit {
                    update = .available(sha: shortRemote, message: msg)
                } else {
                    update = .upToDate(shortRemote)
                }
            } else {
                update = .failed("Could not read GitHub reply")
            }
        } catch {
            update = .failed("Offline")
        }
    }
}
