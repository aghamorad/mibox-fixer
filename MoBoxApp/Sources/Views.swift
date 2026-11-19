import SwiftUI
import AppKit
import CoreImage.CIFilterBuiltins

enum SidebarSection: String, CaseIterable, Identifiable {
    case simple, remote, apps, debloat, slideshow, firmware, phone, about
    var id: String { rawValue }

    var title: String {
        switch self {
        case .simple: return "Simple Setup (75)"
        case .remote: return "Couch TV Remote"
        case .apps: return "Apps (Model-Matched)"
        case .debloat: return "Safe Debloat"
        case .slideshow: return "4K Space & Nature"
        case .firmware: return "Firmware & Health"
        case .phone: return "Phone Web App"
        case .about: return "What it does"
        }
    }

    var icon: String {
        switch self {
        case .simple: return "sparkles.tv"
        case .remote: return "av.remote"
        case .apps: return "square.grid.2x2"
        case .debloat: return "leaf"
        case .slideshow: return "moon.stars"
        case .firmware: return "cpu"
        case .phone: return "iphone.radiowaves.left.and.right"
        case .about: return "info.circle"
        }
    }
}

struct RootView: View {
    @EnvironmentObject private var model: AppModel
    @State private var selection: SidebarSection = .simple

    var visibleSections: [SidebarSection] {
        if model.uiMode == "simple" {
            return [.simple, .remote, .slideshow, .phone, .about]
        }
        return SidebarSection.allCases
    }

    var body: some View {
        NavigationSplitView {
            VStack(alignment: .leading, spacing: 0) {
                ScrollView {
                    VStack(alignment: .leading, spacing: 4) {
                        HStack(spacing: 8) {
                            Image(systemName: "tv.and.mediabox")
                                .font(.title3)
                                .foregroundStyle(.orange)
                            Text("MoBox")
                                .font(.headline)
                                .fontWeight(.bold)
                        }
                        .padding(.horizontal, 10)
                        .padding(.top, 16)
                        .padding(.bottom, 6)

                        Picker("Mode", selection: $model.uiMode) {
                            Text("Simple (75)").tag("simple")
                            Text("Advanced (35)").tag("advanced")
                        }
                        .pickerStyle(.segmented)
                        .padding(.horizontal, 8)
                        .padding(.bottom, 10)
                        .onChange(of: model.uiMode) { newMode in
                            if newMode == "simple" && !visibleSections.contains(selection) {
                                selection = .simple
                            }
                        }

                        ForEach(visibleSections) { item in
                            SidebarRow(item: item, selected: selection == item) {
                                selection = item
                            }
                        }
                    }
                    .padding(.horizontal, 10)
                }
                Divider()
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text("Made by Morad")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Spacer()
                        Button {
                            Task { await model.checkForUpdate() }
                        } label: {
                            Text("v\(model.appVersion) (\(model.buildCommit))")
                                .font(.caption)
                                .foregroundStyle(.tertiary)
                        }
                        .buttonStyle(.plain)
                        .help("Check GitHub for a newer commit")
                    }
                    updateLine
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
            }
            .navigationSplitViewColumnWidth(min: 215, ideal: 230, max: 270)
        } detail: {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    connectionBanner
                    pageContent
                }
                .padding(24)
            }
            .frame(minWidth: 640, minHeight: 520)
        }
        .toolbar {
            ToolbarItemGroup(placement: .automatic) {
                if model.status.busy {
                    HStack(spacing: 6) {
                        ProgressView().controlSize(.small)
                        Text(model.status.progress.label)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                Button {
                    Task { await model.refresh(forceScan: true) }
                } label: {
                    Label("Find Mi Box", systemImage: "arrow.clockwise")
                }
                .help("Scan home Wi-Fi for your Mi Box")
            }
        }
        .overlay(alignment: .bottom) {
            if let notice = model.notice, !notice.isEmpty {
                HStack(spacing: 10) {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(.green)
                    Text(notice)
                        .font(.callout)
                        .fontWeight(.medium)
                    Button("OK") { model.notice = nil }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .background(.ultraThinMaterial, in: Capsule())
                .shadow(radius: 8)
                .padding(.bottom, 16)
            }
        }
    }

    @ViewBuilder
    private var updateLine: some View {
        switch model.update {
        case .idle:
            EmptyView()
        case .checking:
            Text("Checking GitHub…").font(.caption2).foregroundStyle(.secondary)
        case .upToDate(let sha):
            Text("Up to date (\(sha))").font(.caption2).foregroundStyle(.green)
        case .available(let sha, let msg):
            Button {
                if let url = URL(string: "https://github.com/aghamorad/mibox-fixer") {
                    NSWorkspace.shared.open(url)
                }
            } label: {
                Text("New commit \(sha): \(msg)")
                    .font(.caption2)
                    .foregroundStyle(.orange)
                    .lineLimit(1)
            }
            .buttonStyle(.plain)
        case .failed(let reason):
            Text("Update check: \(reason)").font(.caption2).foregroundStyle(.secondary)
        }
    }

    // MARK: - Connection Banner

    private var connectionBanner: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Image(systemName: model.status.connected ? "checkmark.seal.fill" : "wifi.exclamationmark")
                        .font(.title2)
                        .foregroundStyle(model.status.connected ? .green : .orange)
                    if let fw = model.status.firmware, model.status.connected {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Connected to \(fw.model) (\(model.status.serial ?? ""))")
                                .font(.headline)
                            Text("Android \(fw.android_release) • \(fw.arch_label) • Firmware \(fw.build_id) • \(fw.free_storage_mb ?? 0) MB free")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                    } else {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Searching for your Mi Box on home Wi-Fi…")
                                .font(.headline)
                            Text("Make sure your TV and Mi Box are on the same Wi-Fi network.")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                    }
                    Spacer()
                    Button("Auto-Find on Wi-Fi") {
                        Task { await model.refresh(forceScan: true) }
                    }
                    .controlSize(.large)
                }

                HStack(spacing: 8) {
                    TextField("Mi Box IP (e.g. 192.168.0.117)", text: $model.manualIP)
                        .textFieldStyle(.roundedBorder)
                        .frame(maxWidth: 220)
                    Button("Connect by IP") {
                        Task { await model.connectManual() }
                    }
                    if let fw = model.status.firmware, model.status.connected {
                        Spacer()
                        StatusPill(label: "TV Wake", ok: fw.tv_wake_ready)
                        StatusPill(label: "MATVT Mouse", ok: fw.matvt_active)
                        StatusPill(label: "4K Slideshow", ok: fw.aerialviews_active)
                    }
                }
            }
            .padding(6)
        }
    }

    // MARK: - Pages

    @ViewBuilder
    private var pageContent: some View {
        switch selection {
        case .simple:
            simplePage
        case .remote:
            remotePage
        case .apps:
            appsPage
        case .debloat:
            debloatPage
        case .slideshow:
            slideshowPage
        case .firmware:
            firmwarePage
        case .phone:
            phonePage
        case .about:
            aboutPage
        }
    }

    // 1. Simple (75-Year-Old Mode) Page
    private var simplePage: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("One button checks your Mi Box firmware and applies your complete clean setup without removing any existing apps.")
                .font(.callout)
                .foregroundStyle(.secondary)

            GroupBox {
                VStack(alignment: .leading, spacing: 14) {
                    Text("Make My Mi Box Ready (All-in-One)")
                        .font(.title2)
                        .fontWeight(.bold)

                    VStack(alignment: .leading, spacing: 6) {
                        Label("Clean Apple TV-style home screen (Hume), Live TV, Ad-free YouTube, Browser & SlamVision", systemImage: "checkmark.circle.fill")
                        Label("4K Outer Space & Nature Slideshow (Aerial Views) after 5 minutes idle", systemImage: "checkmark.circle.fill")
                        Label("Fixes TV-remote auto-wake so turning on your TV always finds the Mi Box awake", systemImage: "checkmark.circle.fill")
                        Label("Activates the Mouse & Scroll Helper (MATVT) and keeps all your existing apps safe", systemImage: "checkmark.circle.fill")
                    }
                    .font(.body)

                    Button {
                        Task { await model.runSimpleSetup() }
                    } label: {
                        HStack {
                            Image(systemName: "sparkles")
                            Text(model.status.busy ? "Setting Up Your Mi Box…" : "Set Up My Mi Box Now")
                                .fontWeight(.bold)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.green)
                    .controlSize(.large)
                    .disabled(model.status.busy || !model.status.connected)

                    ProgressView(
                        value: Double(model.status.progress.step),
                        total: Double(max(1, model.status.progress.total))
                    )
                    Text(model.status.progress.label)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                }
                .padding(10)
            }

            HStack(spacing: 14) {
                GroupBox {
                    VStack(alignment: .leading, spacing: 10) {
                        Label("4K Space & Nature Slideshow", systemImage: "moon.stars.fill")
                            .font(.headline)
                        Text("Starts automatically after 5 minutes idle, or click below to watch it on your TV right now.")
                            .font(.callout)
                            .foregroundStyle(.secondary)
                        Button("Start 4K Slideshow on TV") {
                            Task { await model.performAction("slideshow") }
                        }
                        .controlSize(.large)
                    }
                    .padding(8)
                    .frame(maxWidth: .infinity, alignment: .leading)
                }

                GroupBox {
                    VStack(alignment: .leading, spacing: 10) {
                        Label("Pair Apple Magic Mouse", systemImage: "magicmouse.fill")
                            .font(.headline)
                        Text("Flip your Magic Mouse off and back on, then click below to open Bluetooth pairing on your TV.")
                            .font(.callout)
                            .foregroundStyle(.secondary)
                        Button("Open Bluetooth Pairing on TV") {
                            Task { await model.performAction("bluetooth") }
                        }
                        .controlSize(.large)
                    }
                    .padding(8)
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }

    // 2. Couch TV Remote Page
    private var remotePage: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Drive your Mi Box over Wi-Fi when the physical remote is across the room.")
                .font(.callout)
                .foregroundStyle(.secondary)

            HStack(alignment: .top, spacing: 20) {
                GroupBox("D-Pad Remote") {
                    VStack(spacing: 10) {
                        HStack(spacing: 10) {
                            remoteButton("Back", key: "BACK", icon: "arrow.uturn.backward")
                            remoteButton("Up", key: "UP", icon: "chevron.up")
                            remoteButton("Home", key: "HOME", icon: "house.fill")
                        }
                        HStack(spacing: 10) {
                            remoteButton("Left", key: "LEFT", icon: "chevron.left")
                            Button {
                                Task { await model.performAction("key", extra: ["key": "OK"]) }
                            } label: {
                                Text("OK")
                                    .font(.headline)
                                    .frame(width: 84, height: 48)
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(.orange)
                            remoteButton("Right", key: "RIGHT", icon: "chevron.right")
                        }
                        HStack(spacing: 10) {
                            remoteButton("Vol −", key: "VOL_DOWN", icon: "speaker.Wave.1.fill")
                            remoteButton("Down", key: "DOWN", icon: "chevron.down")
                            remoteButton("Vol +", key: "VOL_UP", icon: "speaker.wave.3.fill")
                        }
                    }
                    .padding(10)
                }

                GroupBox("Open App on TV") {
                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(model.status.apps.filter { $0.can_launch && $0.installed }) { app in
                            Button {
                                Task { await model.performAction("launch_app", extra: ["app": app.key]) }
                            } label: {
                                HStack {
                                    Image(systemName: "play.tv.fill")
                                    Text(app.title)
                                    Spacer()
                                }
                                .frame(maxWidth: .infinity)
                            }
                            .controlSize(.large)
                        }
                    }
                    .padding(10)
                    .frame(maxWidth: .infinity)
                }
            }
        }
    }

    private func remoteButton(_ title: String, key: String, icon: String) -> some View {
        Button {
            Task { await model.performAction("key", extra: ["key": key]) }
        } label: {
            VStack(spacing: 4) {
                Image(systemName: icon)
                Text(title).font(.caption)
            }
            .frame(width: 84, height: 48)
        }
    }

    // 3. Model-Matched Apps Page
    private var appsPage: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("MoBox inspects your box's CPU (\(model.status.firmware?.arch_label ?? "32-bit / 64-bit")) and picks the matching APK build automatically.")
                .font(.callout)
                .foregroundStyle(.secondary)

            ForEach(model.status.apps) { app in
                GroupBox {
                    HStack(spacing: 14) {
                        VStack(alignment: .leading, spacing: 4) {
                            HStack(spacing: 8) {
                                Text(app.title).font(.headline)
                                if app.installed {
                                    Text("Installed")
                                        .font(.caption2)
                                        .padding(.horizontal, 8)
                                        .padding(.vertical, 2)
                                        .background(Color.green.opacity(0.2), in: Capsule())
                                }
                                Text(app.asset)
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                            Text(app.detail)
                                .font(.callout)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        if app.can_launch && app.installed {
                            Button("Open on TV") {
                                Task { await model.performAction("launch_app", extra: ["app": app.key]) }
                            }
                        }
                        Button(app.installed ? "Reinstall" : "Install") {
                            Task { await model.performAction("install_app", extra: ["app": app.key]) }
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(model.status.busy)
                    }
                    .padding(6)
                }
            }
        }
    }

    // 4. Safe Debloat Page
    private var debloatPage: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Nothing is uninstalled. Packages are disabled with pm disable-user and can be restored anytime.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                Spacer()
                Button("Disable All Safe Bloat") {
                    Task { await model.performAction("debloat_safe") }
                }
                .buttonStyle(.borderedProminent)
                .tint(.orange)
            }

            ForEach(model.status.bloat) { b in
                GroupBox {
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            HStack(spacing: 6) {
                                Text(b.title).font(.headline)
                                Text(b.category).font(.caption).foregroundStyle(.secondary)
                                if b.disabled {
                                    Text("Disabled")
                                        .font(.caption2)
                                        .padding(.horizontal, 6)
                                        .padding(.vertical, 2)
                                        .background(Color.orange.opacity(0.2), in: Capsule())
                                }
                            }
                            Text(b.detail).font(.caption).foregroundStyle(.secondary)
                        }
                        Spacer()
                        Button(b.disabled ? "Restore" : "Disable") {
                            Task {
                                await model.performAction(
                                    "toggle_package",
                                    extra: ["package": b.package, "disable": !b.disabled]
                                )
                            }
                        }
                    }
                    .padding(4)
                }
            }
        }
    }

    // 5. 4K Space & Nature Slideshow Page
    private var slideshowPage: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Aerial Views plays 250+ 4K Outer Space (ISS Earth orbit, night sky) and Nature scenes, plus the 15 offline 4K NASA James Webb & Nature wallpapers in /sdcard/Wallpapers.")
                .font(.callout)
                .foregroundStyle(.secondary)

            GroupBox("Slideshow Controls") {
                VStack(alignment: .leading, spacing: 12) {
                    HStack(spacing: 12) {
                        Button("Start 4K Space & Nature Slideshow Now") {
                            Task { await model.performAction("slideshow") }
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.large)

                        Button("Open Aerial Views Settings on TV") {
                            Task { await model.performAction("launch_app", extra: ["app": "aerialviews"]) }
                        }
                        .controlSize(.large)
                    }
                    Text("Tip: While the slideshow is playing on your TV, press Left or Right on your Samsung TV remote to skip to the next 4K Space or Nature scene.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(8)
            }
        }
    }

    // 6. Firmware & Health Page
    private var firmwarePage: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Live hardware, kernel HID, and HDMI-CEC deep-sleep diagnostics read directly from the connected box.")
                .font(.callout)
                .foregroundStyle(.secondary)

            if let fw = model.status.firmware {
                GroupBox("Hardware & Firmware") {
                    VStack(alignment: .leading, spacing: 6) {
                        infoRow("Model / Codename", "\(fw.model) / \(fw.product)")
                        infoRow("Android / SDK", "Android \(fw.android_release) (SDK \(fw.sdk))")
                        infoRow("Firmware Build", "\(fw.build_id) (Security patch: \(fw.security_patch))")
                        infoRow("Linux Kernel", fw.kernel)
                        infoRow("CPU Architecture", "\(fw.arch_label) (\(fw.abis.joined(separator: ", ")))")
                        infoRow("Free Space / RAM", "\(fw.free_storage_mb ?? 0) MB storage / \(fw.free_ram_mb ?? 0) MB RAM")
                    }
                    .padding(8)
                }

                GroupBox("TV Remote Auto-Wake & Apple Magic Mouse") {
                    VStack(alignment: .leading, spacing: 6) {
                        infoRow("HDMI-CEC (Anynet+)", fw.hdmi_cec_enabled ? "Enabled" : "Disabled")
                        infoRow("TV Auto-Device-Off Bug", fw.hdmi_auto_device_off == false ? "OFF (Safe — no deep-sleep coma)" : "ON (Causes deep-sleep coma)")
                        infoRow("Kernel HID Drivers", fw.hid_drivers.joined(separator: ", "))
                        infoRow("Kernel hid-magicmouse", fw.has_magicmouse_driver ? "Present" : "Not in kernel (pointer+click work; use MATVT for scroll)")
                        infoRow("MATVT Mouse Helper", fw.matvt_active ? "Active (AccessibilityService bound)" : "Not enabled")
                        infoRow("4K Space Slideshow", fw.aerialviews_active ? "Active (5-minute DreamService)" : "Not enabled")
                    }
                    .padding(8)
                }
            } else {
                Text("Connect to a Mi Box to view firmware diagnostics.")
                    .foregroundStyle(.secondary)
            }
        }
    }

    private func infoRow(_ key: String, _ val: String) -> some View {
        HStack {
            Text(key).fontWeight(.semibold).frame(width: 190, alignment: .leading)
            Text(val).foregroundStyle(.secondary)
            Spacer()
        }
    }

    // 7. Phone Web App Page (with native QR Code!)
    private var phonePage: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Scan this QR code with your iPhone or Android phone camera on the same Wi-Fi to open the MoBox Phone Web App from the couch.")
                .font(.callout)
                .foregroundStyle(.secondary)

            GroupBox {
                HStack(spacing: 24) {
                    if let qr = makeQRCode(from: model.phoneWebURL) {
                        Image(nsImage: qr)
                            .interpolation(.none)
                            .resizable()
                            .frame(width: 160, height: 160)
                            .cornerRadius(12)
                    }
                    VStack(alignment: .leading, spacing: 10) {
                        Text("Phone & Browser Web App")
                            .font(.title3)
                            .fontWeight(.bold)
                        Text(model.phoneWebURL)
                            .font(.system(.title3, design: .monospaced))
                            .foregroundStyle(.orange)
                        Text("Gives your phone the Simple (75-Year-Old) 1-tap setup, Advanced (35-Year-Old) app manager, and a live Couch TV Remote.")
                            .font(.callout)
                            .foregroundStyle(.secondary)
                        HStack(spacing: 10) {
                            Button("Open in Browser on Mac") {
                                if let u = URL(string: model.phoneWebURL) {
                                    NSWorkspace.shared.open(u)
                                }
                            }
                            .buttonStyle(.borderedProminent)
                            Button("Copy Link") {
                                NSPasteboard.general.clearContents()
                                NSPasteboard.general.setString(model.phoneWebURL, forType: .string)
                                model.notice = "Copied \(model.phoneWebURL) to clipboard"
                            }
                        }
                    }
                    Spacer()
                }
                .padding(12)
            }
        }
    }

    // 8. What It Does Page
    private var aboutPage: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Everything MoBox changes, what it never touches, and how to undo any step.")
                .font(.callout)
                .foregroundStyle(.secondary)

            GroupBox("What MoBox does") {
                VStack(alignment: .leading, spacing: 8) {
                    Text("• Auto-discovers your Mi Box or Android TV on home Wi-Fi and reads its exact CPU architecture (32-bit armeabi-v7a vs 64-bit arm64-v8a) and firmware.")
                    Text("• Installs verified open-source TV apps (Hume Launcher, TV Bro 3.0.5 geckoExcluded, TV Live IPTV, SmartTube, SlamVision, MATVT Mouse Helper, and Aerial Views 4K Space & Nature Slideshow).")
                    Text("• Temporarily toggles Play Protect's ADB verifier only if an install is blocked, and always restores it immediately.")
                    Text("• Fixes the Android 9 + Samsung Anynet+ deep-sleep bug (hdmi_control_auto_device_off_enabled=0, sleep_timeout=-1) while enabling the 5-minute 4K Space & Nature slideshow.")
                    Text("• Never deletes your existing apps, bookmarks, or user data.")
                }
                .padding(8)
            }
        }
    }

    private func makeQRCode(from string: String) -> NSImage? {
        let context = CIContext()
        let filter = CIFilter.qrCodeGenerator()
        filter.message = Data(string.utf8)
        filter.correctionLevel = "M"
        guard let output = filter.outputImage else { return nil }
        let scaled = output.transformed(by: CGAffineTransform(scaleX: 8, y: 8))
        guard let cgimg = context.createCGImage(scaled, from: scaled.extent) else { return nil }
        return NSImage(cgImage: cgimg, size: NSSize(width: 160, height: 160))
    }

    private struct SidebarRow: View {
        let item: SidebarSection
        let selected: Bool
        let action: () -> Void

        var body: some View {
            Button(action: action) {
                HStack(spacing: 10) {
                    Image(systemName: item.icon)
                        .frame(width: 20)
                        .foregroundStyle(selected ? .white : .primary)
                    Text(item.title)
                        .fontWeight(selected ? .semibold : .regular)
                        .foregroundStyle(selected ? .white : .primary)
                    Spacer()
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 7)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(selected ? Color.accentColor : Color.clear)
                )
            }
            .buttonStyle(.plain)
        }
    }

    private struct StatusPill: View {
        let label: String
        let ok: Bool
        var body: some View {
            HStack(spacing: 4) {
                Circle()
                    .fill(ok ? Color.green : Color.orange)
                    .frame(width: 7, height: 7)
                Text(label)
                    .font(.caption)
                    .fontWeight(.medium)
            }
            .padding(.horizontal, 9)
            .padding(.vertical, 4)
            .background(Color.primary.opacity(0.06), in: Capsule())
        }
    }
}
