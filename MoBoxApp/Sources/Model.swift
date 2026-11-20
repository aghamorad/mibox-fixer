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
    case upToDate
    case available(summary: String)
    case updating
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

    private static func isPortOpen(_ port: UInt16) -> Bool {
        let fd = socket(AF_INET, SOCK_STREAM, 0)
        guard fd >= 0 else { return false }
        defer { close(fd) }
        var addr = sockaddr_in()
        addr.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = port.bigEndian
        addr.sin_addr.s_addr = inet_addr("127.0.0.1")
        let res = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                connect(fd, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        return res == 0
    }

    func startBackendIfNeeded() {
        if serverProcess?.isRunning == true || Self.isPortOpen(UInt16(serverPort)) { return }
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

    func sendPointerUDP(_ cmd: String) {
        let host = (status.serial?.split(separator: ":").first.map(String.init)) ?? manualIP
        guard !host.isEmpty else { return }
        DispatchQueue.global(qos: .userInteractive).async {
            let fd = socket(AF_INET, SOCK_DGRAM, 0)
            guard fd >= 0 else { return }
            defer { close(fd) }
            var addr = sockaddr_in()
            addr.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
            addr.sin_family = sa_family_t(AF_INET)
            addr.sin_port = UInt16(8766).bigEndian
            addr.sin_addr.s_addr = inet_addr(host)
            let bytes = Array(cmd.utf8)
            _ = bytes.withUnsafeBytes { rawBuf in
                withUnsafePointer(to: &addr) {
                    $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { sa in
                        sendto(fd, rawBuf.baseAddress, bytes.count, 0, sa, socklen_t(MemoryLayout<sockaddr_in>.size))
                    }
                }
            }
        }
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
                    update = .available(summary: msg)
                } else {
                    update = .upToDate
                }
            } else {
                update = .failed("Could not check for updates")
            }
        } catch {
            update = .failed("Offline")
        }
    }

    func installUpdate() async {
        guard case .available = update else { return }
        update = .updating
        notice = "Downloading the latest MoBox update…"
        let zipURL = URL(string: "https://raw.githubusercontent.com/aghamorad/mibox-fixer/main/docs/downloads/MoBox-Mac-universal.zip")!
        do {
            let (tmpZip, _) = try await URLSession.shared.download(from: zipURL)
            let workDir = FileManager.default.temporaryDirectory.appendingPathComponent("mobox-update-\(UUID().uuidString)")
            try FileManager.default.createDirectory(at: workDir, withIntermediateDirectories: true)

            let unzip = Process()
            unzip.executableURL = URL(fileURLWithPath: "/usr/bin/ditto")
            unzip.arguments = ["-xk", tmpZip.path, workDir.path]
            try unzip.run()
            unzip.waitUntilExit()

            let newApp = workDir.appendingPathComponent("MoBox.app")
            guard unzip.terminationStatus == 0,
                  FileManager.default.fileExists(atPath: newApp.appendingPathComponent("Contents/MacOS/MoBox").path) else {
                update = .failed("Downloaded update could not be unpacked.")
                return
            }

            let targetApp = Bundle.main.bundleURL.path.hasSuffix(".app")
                ? Bundle.main.bundleURL
                : URL(fileURLWithPath: "/Applications/MoBox.app")
            let trashApp = FileManager.default.homeDirectoryForCurrentUser
                .appendingPathComponent(".Trash/MoBox-old-\(Int(Date().timeIntervalSince1970)).app")

            stopBackend()
            if FileManager.default.fileExists(atPath: targetApp.path) {
                try FileManager.default.moveItem(at: targetApp, to: trashApp)
            }
            try FileManager.default.moveItem(at: newApp, to: targetApp)

            let relaunch = Process()
            relaunch.executableURL = URL(fileURLWithPath: "/usr/bin/open")
            relaunch.arguments = ["-n", targetApp.path]
            try relaunch.run()
            NSApp.terminate(nil)
        } catch {
            update = .failed("Update failed: \(error.localizedDescription)")
        }
    }
}
