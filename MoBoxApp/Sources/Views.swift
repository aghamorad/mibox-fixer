import SwiftUI
import AppKit
import CoreImage.CIFilterBuiltins

enum SidebarSection: String, CaseIterable, Identifiable {
    case home, remote, apps, debloat, slideshow, health, phone, about
    var id: String { rawValue }

    var title: String {
        switch self {
        case .home: return "Home"
        case .remote: return "TV remote"
        case .apps: return "Apps"
        case .debloat: return "Clutter"
        case .slideshow: return "4K backgrounds"
        case .health: return "Box & firmware"
        case .phone: return "Phone control"
        case .about: return "What it does"
        }
    }

    var icon: String {
        switch self {
        case .home: return "house"
        case .remote: return "av.remote"
        case .apps: return "square.grid.2x2"
        case .debloat: return "eye.slash"
        case .slideshow: return "photo.on.rectangle.angled"
        case .health: return "cpu"
        case .phone: return "qrcode"
        case .about: return "info.circle"
        }
    }
}

// MARK: - Root

struct RootView: View {
    @EnvironmentObject private var model: AppModel
    @State private var selection: SidebarSection? = .home

    var visibleSections: [SidebarSection] {
        if model.uiMode == "simple" {
            return [.home, .remote, .slideshow, .phone, .about]
        }
        return SidebarSection.allCases
    }

    var body: some View {
        NavigationSplitView {
            VStack(alignment: .leading, spacing: 0) {
                ScrollView {
                    VStack(alignment: .leading, spacing: 2) {
                        HStack(alignment: .firstTextBaseline) {
                            Text("MOBOX")
                                .font(.caption).fontWeight(.semibold)
                                .foregroundStyle(.secondary)
                            Spacer()
                        }
                        .padding(.horizontal, 10)
                        .padding(.top, 16)
                        .padding(.bottom, 6)

                        Picker("", selection: $model.uiMode) {
                            Text("Simple").tag("simple")
                            Text("Advanced").tag("advanced")
                        }
                        .pickerStyle(.segmented)
                        .labelsHidden()
                        .padding(.horizontal, 8)
                        .padding(.bottom, 10)
                        .onChange(of: model.uiMode) { newMode in
                            if newMode == "simple", let cur = selection, !visibleSections.contains(cur) {
                                selection = .home
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
                            Text("v\(model.appVersion)")
                                .font(.caption)
                                .foregroundStyle(.tertiary)
                        }
                        .buttonStyle(.plain)
                        .help("Check GitHub for a newer version")
                    }
                    updateLine
                }
                .padding(.horizontal, 14)
                .padding(.vertical, 8)
            }
            .navigationSplitViewColumnWidth(min: 205, ideal: 220, max: 260)
        } detail: {
            page
                .frame(minWidth: 620, minHeight: 480)
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
                    Image(systemName: "arrow.clockwise")
                }
                .help("Read the box again")
                .disabled(model.status.busy)
            }
        }
        .overlay(alignment: .bottom) {
            if let notice = model.notice, !notice.isEmpty {
                NoticeToast(text: notice) { model.notice = nil }
                    .padding(.horizontal, 24)
                    .padding(.bottom, 18)
                    .transition(.opacity.combined(with: .move(edge: .bottom)))
            }
        }
        .animation(.easeInOut(duration: 0.18), value: model.notice)
    }

    private struct SidebarRow: View {
        let item: SidebarSection
        let selected: Bool
        let action: () -> Void

        var body: some View {
            Button(action: action) {
                Label(item.title, systemImage: item.icon)
                    .font(.system(size: 15, weight: selected ? .semibold : .regular))
                    .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
                    .padding(.horizontal, 12)
                    .contentShape(Rectangle())
                    .background(
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .fill(selected ? Color.accentColor : Color.clear)
                    )
                    .foregroundStyle(selected ? Color.white : Color.primary)
            }
            .buttonStyle(.plain)
        }
    }

    @ViewBuilder
    private var page: some View {
        switch selection ?? .home {
        case .home:
            HomeView(section: $selection)
        case .remote:
            RemoteView()
        case .apps:
            AppsView()
        case .debloat:
            DebloatView()
        case .slideshow:
            SlideshowView()
        case .health:
            HealthView()
        case .phone:
            PhoneView()
        case .about:
            ScopeView()
        }
    }

    @ViewBuilder
    private var updateLine: some View {
        switch model.update {
        case .idle:
            EmptyView()
        case .checking:
            HStack(spacing: 5) {
                ProgressView().controlSize(.mini)
                Text("Checking GitHub…").font(.caption2).foregroundStyle(.secondary)
            }
        case .upToDate(let sha):
            Text("Up to date (\(sha))")
                .font(.caption2).foregroundStyle(.secondary)
        case .available(let sha, let msg):
            Button {
                if let url = URL(string: "https://github.com/aghamorad/mibox-fixer") {
                    NSWorkspace.shared.open(url)
                }
            } label: {
                Label("New commit \(sha): \(msg)", systemImage: "arrow.down.circle.fill")
                    .font(.caption2)
                    .lineLimit(1)
            }
            .buttonStyle(.plain)
            .foregroundStyle(Color.accentColor)
        case .failed(let reason):
            Text(reason).font(.caption2).foregroundStyle(.secondary)
        }
    }
}

// MARK: - 1. Home

struct HomeView: View {
    @EnvironmentObject private var model: AppModel
    @Binding var section: SidebarSection?
    @State private var showIPInput = false

    private var fw: FirmwareInfo? { model.status.firmware }
    private var allReady: Bool {
        guard let fw else { return false }
        return fw.tv_wake_ready && fw.matvt_active && fw.aerialviews_active
    }

    var body: some View {
        PageScroll {
            PageHeader(
                title: "MoBox",
                subtitle: "Your TV box, set up cleanly in one click."
            )

            ScopeNote("Installs missing apps and fixes sleep and remote settings. It never deletes your existing apps or data.")

            heroCard

            if model.status.connected {
                quickActionsRow
            } else {
                connectCard
            }

            if let fw, model.status.connected {
                HStack(alignment: .top, spacing: 16) {
                    boxSummaryCard(fw)
                    setupChecklistCard(fw)
                }
            }

            InfoBox(
                title: "What the setup button actually does",
                text: "It reads your box's processor (32-bit or 64-bit), installs any missing "
                    + "core apps (Hume home screen, TV Live, SmartTube, TV Bro, SlamVision, "
                    + "MATVT mouse helper, and Aerial Views 4K Space & Nature slideshow), "
                    + "stops your TV from locking the box in Android 9's deep-sleep coma, "
                    + "and sets Hume as the home screen. Safe to run again at any time."
            )
        }
    }

    private var heroCard: some View {
        let copy = heroCopy()
        return VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .top, spacing: 20) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(copy.title)
                        .font(.system(size: 28, weight: .semibold, design: .rounded))
                    Text(copy.detail)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 12)
                Button {
                    Task { await model.runSimpleSetup() }
                } label: {
                    Label(
                        model.status.busy ? "Working…" : (allReady ? "Run Setup Again" : "Set Up Mi Box"),
                        systemImage: allReady ? "checkmark.circle" : "arrow.down.app.fill"
                    )
                    .font(.system(size: 15, weight: .semibold))
                    .frame(minWidth: 165, minHeight: 46)
                }
                .buttonStyle(.borderedProminent)
                .tint(allReady ? .accentColor : .green)
                .disabled(!model.status.connected || model.status.busy)
            }

            if model.status.busy {
                VStack(alignment: .leading, spacing: 6) {
                    ProgressView(
                        value: Double(model.status.progress.step),
                        total: Double(max(1, model.status.progress.total))
                    )
                    Text(model.status.progress.label)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Divider()

            HStack(spacing: 26) {
                miniStat(
                    label: "Box",
                    value: model.status.connected ? (fw?.model ?? "Connected") : "Not found",
                    ok: model.status.connected
                )
                miniStat(
                    label: "TV remote wake",
                    value: fw?.tv_wake_ready == true ? "Protected" : "Needs fix",
                    ok: fw?.tv_wake_ready == true
                )
                miniStat(
                    label: "Mouse helper",
                    value: fw?.matvt_active == true ? "Active" : "Off",
                    ok: fw?.matvt_active == true
                )
                miniStat(
                    label: "4K slideshow",
                    value: fw?.aerialviews_active == true ? "5 min idle" : "Off",
                    ok: fw?.aerialviews_active == true
                )
            }
        }
        .padding(22)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(Color(nsColor: .controlBackgroundColor))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .strokeBorder(Color.primary.opacity(0.07))
        )
    }

    private func heroCopy() -> (title: String, detail: String) {
        if !model.status.connected {
            return (
                "Looking for your Mi Box",
                "Make sure your TV and Mi Box are on and connected to the same Wi-Fi network as this Mac."
            )
        }
        if model.status.busy {
            return (
                "Setting up your Mi Box",
                model.status.progress.label
            )
        }
        if allReady {
            return (
                "Your Mi Box is ready",
                "TV-remote auto-wake is protected, MATVT mouse helper is active, and the 4K Space & Nature slideshow starts after 5 minutes idle."
            )
        }
        return (
            "Ready to set up",
            "Press Set Up Mi Box to install missing apps, protect TV-remote wake-up, and turn on the 4K Space & Nature slideshow."
        )
    }

    private var connectCard: some View {
        Card {
            VStack(alignment: .leading, spacing: 12) {
                Text("Connect to your box").font(.headline)
                Text("MoBox scans your Wi-Fi automatically. If your box is on a different address, type its IP below (found on the TV under Settings → Network → Wi-Fi).")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                HStack(spacing: 10) {
                    TextField("192.168.0.117", text: $model.manualIP)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 180)
                    Button("Connect") {
                        Task { await model.connectManual() }
                    }
                    .controlSize(.large)
                    Button("Scan Wi-Fi Again") {
                        Task { await model.refresh(forceScan: true) }
                    }
                    .controlSize(.large)
                }
            }
        }
    }

    private var quickActionsRow: some View {
        HStack(spacing: 12) {
            quickButton(title: "Start 4K Slideshow", icon: "photo.on.rectangle.angled") {
                Task { await model.performAction("slideshow") }
            }
            quickButton(title: "Pair Apple Magic Mouse", icon: "magicmouse") {
                Task { await model.performAction("bluetooth") }
            }
            quickButton(title: "Open TV Remote", icon: "av.remote") {
                section = .remote
            }
        }
    }

    private func boxSummaryCard(_ fw: FirmwareInfo) -> some View {
        Card {
            VStack(alignment: .leading, spacing: 10) {
                Text("This box").font(.headline)
                InfoRow(label: "Model", value: "\(fw.model) (\(fw.product))")
                InfoRow(label: "Address", value: model.status.serial ?? "—")
                InfoRow(label: "Android", value: "\(fw.android_release) (SDK \(fw.sdk))")
                InfoRow(label: "Processor", value: fw.arch_label)
                InfoRow(label: "Free storage", value: "\(fw.free_storage_mb ?? 0) MB")
            }
        }
    }

    private func setupChecklistCard(_ fw: FirmwareInfo) -> some View {
        Card {
            VStack(alignment: .leading, spacing: 10) {
                Text("What is active").font(.headline)
                InfoRow(label: "TV-remote wake fix", value: fw.tv_wake_ready ? "On (never deep-sleeps)" : "Not applied")
                InfoRow(label: "MATVT mouse & scroll", value: fw.matvt_active ? "On" : "Off")
                InfoRow(label: "4K Space & Nature", value: fw.aerialviews_active ? "On (5 min idle)" : "Off")
                InfoRow(label: "Magic Mouse kernel", value: fw.has_magicmouse_driver ? "Full touch" : "Pointer + click")
                InfoRow(label: "Phone web control", value: model.phoneWebURL)
            }
        }
    }

    private func miniStat(label: String, value: String, ok: Bool) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(label).font(.caption).foregroundStyle(.secondary)
            HStack(spacing: 6) {
                StatusDot(ok: ok)
                Text(value).font(.callout.weight(.medium)).lineLimit(1)
            }
        }
    }

    private func quickButton(title: String, icon: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                Text(title).fontWeight(.medium)
            }
            .frame(maxWidth: .infinity, minHeight: 42)
        }
        .buttonStyle(.bordered)
    }
}

// MARK: - 2. TV Remote

struct RemoteView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        PageScroll {
            PageHeader(
                title: "TV remote",
                subtitle: "Control your Mi Box from this Mac or launch any installed app directly."
            )

            ScopeNote("Sends standard Android TV key presses over Wi-Fi. Does not change any settings.")

            HStack(alignment: .top, spacing: 16) {
                Card {
                    VStack(spacing: 12) {
                        Text("Directional pad").font(.headline).frame(maxWidth: .infinity, alignment: .leading)
                        VStack(spacing: 8) {
                            HStack(spacing: 8) {
                                keyButton("Back", key: "BACK", icon: "arrow.uturn.backward")
                                keyButton("Up", key: "UP", icon: "chevron.up")
                                keyButton("Home", key: "HOME", icon: "house")
                            }
                            HStack(spacing: 8) {
                                keyButton("Left", key: "LEFT", icon: "chevron.left")
                                Button {
                                    Task { await model.performAction("key", extra: ["key": "OK"]) }
                                } label: {
                                    Text("OK")
                                        .font(.system(size: 15, weight: .semibold))
                                        .frame(width: 86, height: 48)
                                }
                                .buttonStyle(.borderedProminent)
                                keyButton("Right", key: "RIGHT", icon: "chevron.right")
                            }
                            HStack(spacing: 8) {
                                keyButton("Vol −", key: "VOL_DOWN", icon: "speaker.minus")
                                keyButton("Down", key: "DOWN", icon: "chevron.down")
                                keyButton("Vol +", key: "VOL_UP", icon: "speaker.plus")
                            }
                        }
                        .padding(.vertical, 6)
                    }
                }

                Card {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("Open on TV").font(.headline)
                        ForEach(model.status.apps.filter { $0.can_launch && $0.installed }) { app in
                            Button {
                                Task { await model.performAction("launch_app", extra: ["app": app.key]) }
                            } label: {
                                HStack {
                                    Text(app.title).fontWeight(.medium)
                                    Spacer()
                                    Image(systemName: "arrow.up.forward.app")
                                        .foregroundStyle(.secondary)
                                }
                                .frame(maxWidth: .infinity, minHeight: 34)
                            }
                            .buttonStyle(.bordered)
                        }
                    }
                }
            }
        }
    }

    private func keyButton(_ label: String, key: String, icon: String) -> some View {
        Button {
            Task { await model.performAction("key", extra: ["key": key]) }
        } label: {
            VStack(spacing: 3) {
                Image(systemName: icon)
                Text(label).font(.caption2)
            }
            .frame(width: 86, height: 48)
        }
        .buttonStyle(.bordered)
    }
}

// MARK: - 3. Apps

struct AppsView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        PageScroll {
            PageHeader(
                title: "Apps",
                subtitle: "Open-source TV apps matched automatically to your box's \(model.status.firmware?.arch_label ?? "32-bit or 64-bit") processor."
            )

            ScopeNote("Downloads directly from each project's official GitHub release. Existing app data and bookmarks are kept.")

            ForEach(model.status.apps) { app in
                Card {
                    HStack(alignment: .top, spacing: 16) {
                        VStack(alignment: .leading, spacing: 5) {
                            HStack(spacing: 8) {
                                Text(app.title).font(.headline)
                                if app.installed {
                                    Chip(text: "Installed", color: .green)
                                }
                                if app.simple_default {
                                    Chip(text: "Core", color: .accentColor)
                                }
                            }
                            Text(app.detail)
                                .font(.callout)
                                .foregroundStyle(.secondary)
                                .fixedSize(horizontal: false, vertical: true)
                            Text("\(app.package) · \(app.asset)")
                                .font(.caption)
                                .foregroundStyle(.tertiary)
                        }
                        Spacer(minLength: 12)
                        HStack(spacing: 8) {
                            if app.can_launch && app.installed {
                                Button("Open") {
                                    Task { await model.performAction("launch_app", extra: ["app": app.key]) }
                                }
                                .controlSize(.large)
                            }
                            Button(app.installed ? "Reinstall" : "Install") {
                                Task { await model.performAction("install_app", extra: ["app": app.key]) }
                            }
                            .buttonStyle(.borderedProminent)
                            .controlSize(.large)
                            .disabled(model.status.busy)
                        }
                    }
                }
            }
        }
    }
}

// MARK: - 4. Clutter (Debloat)

struct DebloatView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        PageScroll {
            PageHeader(
                title: "Clutter",
                subtitle: "Preloaded ads, telemetry, and unused stock apps."
            )

            ScopeNote("Uses pm disable-user. Nothing is deleted from the box, and any item can be switched back on here.")

            Card {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Recommended cleanup").font(.headline)
                        Text("Disables preloaded streaming bloat, telemetry, and recommendation rows while leaving system essentials alone.")
                            .font(.callout)
                            .foregroundStyle(.secondary)
                    }
                    Spacer(minLength: 12)
                    Button("Disable Safe Clutter") {
                        Task { await model.performAction("debloat_safe") }
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)
                    .disabled(model.status.busy)
                }
            }

            ForEach(model.status.bloat) { item in
                Card {
                    HStack(spacing: 14) {
                        VStack(alignment: .leading, spacing: 3) {
                            HStack(spacing: 8) {
                                Text(item.title).font(.headline)
                                Chip(text: item.category)
                                if item.disabled {
                                    Chip(text: "Disabled", color: .orange)
                                }
                                if item.danger {
                                    Chip(text: "Manual only", color: .red)
                                }
                            }
                            Text(item.detail)
                                .font(.callout)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        Button(item.disabled ? "Restore" : "Disable") {
                            Task {
                                await model.performAction(
                                    "toggle_package",
                                    extra: ["package": item.package, "disable": !item.disabled]
                                )
                            }
                        }
                        .controlSize(.large)
                    }
                }
            }
        }
    }
}

// MARK: - 5. 4K Backgrounds

struct SlideshowView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        PageScroll {
            PageHeader(
                title: "4K Space & Nature backgrounds",
                subtitle: "Outer space, ISS Earth orbit, and nature scenes that play automatically when the TV sits idle."
            )

            ScopeNote("Runs Aerial Views as Android TV's 5-minute screensaver while keeping deep sleep disabled so your TV remote always wakes the box.")

            StepCard(
                number: 1,
                title: "5-minute 4K Space & Nature slideshow",
                detail: "After 5 minutes on the home screen, Aerial Views plays 250+ 4K Space and Nature videos plus the 15 offline 4K NASA James Webb and Nature wallpapers stored in /sdcard/Wallpapers on your box.",
                done: model.status.firmware?.aerialviews_active == true
            ) {
                HStack(spacing: 10) {
                    Button("Start Slideshow on TV Now") {
                        Task { await model.performAction("slideshow") }
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)

                    Button("Open Aerial Views Settings on TV") {
                        Task { await model.performAction("launch_app", extra: ["app": "aerialviews"]) }
                    }
                    .controlSize(.large)
                }
            }

            InfoBox(
                title: "Skipping scenes with your TV remote",
                text: "While the slideshow is playing, press Left or Right on your Samsung TV remote to jump to the next Space or Nature scene. Press Back or Home to return to your apps."
            )
        }
    }
}

// MARK: - 6. Box & Firmware

struct HealthView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        PageScroll {
            PageHeader(
                title: "Box & firmware",
                subtitle: "What this Mi Box is running, and why each hardware fix is set the way it is."
            )

            ScopeNote("Read-only hardware and kernel diagnostics from your connected box.")

            if let fw = model.status.firmware {
                Card {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("Hardware & software").font(.headline)
                        InfoRow(label: "Model / board", value: "\(fw.model) / \(fw.product)")
                        InfoRow(label: "Android version", value: "Android \(fw.android_release) (SDK \(fw.sdk))")
                        InfoRow(label: "Firmware build", value: fw.build_id)
                        InfoRow(label: "Security patch", value: fw.security_patch)
                        InfoRow(label: "Linux kernel", value: fw.kernel)
                        InfoRow(label: "Supported ABIs", value: fw.abis.joined(separator: ", "))
                        InfoRow(label: "Free storage / RAM", value: "\(fw.free_storage_mb ?? 0) MB / \(fw.free_ram_mb ?? 0) MB")
                    }
                }

                Card {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("HDMI-CEC & Apple Magic Mouse").font(.headline)
                        InfoRow(label: "HDMI-CEC (Anynet+)", value: fw.hdmi_cec_enabled ? "Enabled" : "Disabled")
                        InfoRow(label: "TV-triggered deep sleep", value: fw.hdmi_auto_device_off == false ? "Off (safe — box stays wakeable)" : "On (causes deep-sleep coma)")
                        InfoRow(label: "Kernel HID drivers", value: fw.hid_drivers.joined(separator: ", "))
                        InfoRow(label: "Apple Magic Mouse driver", value: fw.has_magicmouse_driver ? "hid-magicmouse present" : "Not in kernel 4.9 (pointer + click work; MATVT handles scroll)")
                        InfoRow(label: "MATVT accessibility", value: fw.matvt_active ? "Active" : "Inactive")
                        InfoRow(label: "Aerial Views screensaver", value: fw.aerialviews_active ? "Active (5-minute timeout)" : "Inactive")
                    }
                }
            } else {
                InfoBox(
                    title: "No box connected",
                    text: "Connect your Mi Box on the Home page to read its firmware and kernel drivers.",
                    icon: "wifi.exclamationmark"
                )
            }
        }
    }
}

// MARK: - 7. Phone Control

struct PhoneView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        PageScroll {
            PageHeader(
                title: "Phone control",
                subtitle: "Use your iPhone or Android phone on the couch to set up the box or drive it as a remote."
            )

            ScopeNote("Runs locally on your home Wi-Fi while MoBox is open. No account, no cloud server.")

            Card {
                HStack(alignment: .center, spacing: 24) {
                    if let qr = makeQRCode(from: model.phoneWebURL) {
                        Image(nsImage: qr)
                            .interpolation(.none)
                            .resizable()
                            .frame(width: 148, height: 148)
                            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                    }
                    VStack(alignment: .leading, spacing: 10) {
                        Text("Point your phone's camera at the square")
                            .font(.headline)
                        Text(model.phoneWebURL)
                            .font(.system(size: 18, weight: .semibold, design: .monospaced))
                            .textSelection(.enabled)
                        Text("Opens the phone-sized version of MoBox with Simple Setup, Advanced app control, and a full couch remote.")
                            .font(.callout)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                        HStack(spacing: 10) {
                            Button("Open in Browser") {
                                if let url = URL(string: model.phoneWebURL) {
                                    NSWorkspace.shared.open(url)
                                }
                            }
                            .buttonStyle(.borderedProminent)
                            .controlSize(.large)

                            Button("Copy Address") {
                                NSPasteboard.general.clearContents()
                                NSPasteboard.general.setString(model.phoneWebURL, forType: .string)
                                model.notice = "Copied \(model.phoneWebURL)"
                            }
                            .controlSize(.large)
                        }
                    }
                }
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
        return NSImage(cgImage: cgimg, size: NSSize(width: 148, height: 148))
    }
}

// MARK: - 8. What It Does

struct ScopeView: View {
    var body: some View {
        PageScroll {
            PageHeader(
                title: "What it does",
                subtitle: "The whole job in one place: what MoBox changes, what it leaves alone, and why."
            )

            Card {
                VStack(alignment: .leading, spacing: 12) {
                    ScopeRow(
                        label: "What it changes on the box",
                        value: "Installs the apps you pick (Hume Launcher, TV Bro 3.0.5 geckoExcluded, TV Live, SmartTube, SlamVision, MATVT, Aerial Views), enables MATVT's accessibility service and Aerial Views' 5-minute 4K slideshow, and sets hdmi_control_auto_device_off_enabled=0 and sleep_timeout=-1 so turning off the TV never traps the box in deep sleep."
                    )
                    Divider()
                    ScopeRow(
                        label: "What it never touches",
                        value: "Never deletes your existing apps, bookmarks, or files. Clutter cleanup uses pm disable-user so every stock package remains on the system partition and can be re-enabled in one click."
                    )
                    Divider()
                    ScopeRow(
                        label: "Why the Apple Magic Mouse doesn't scroll on glass natively",
                        value: "Xiaomi's Android 9 kernel (Linux 4.9.113) omits the hid-magicmouse driver. Optical pointer movement, left-click, and right-click (Back) work over standard Bluetooth HID, while MATVT gives your Samsung TV remote a virtual pointer and scroll mode."
                    )
                }
            }
        }
    }
}

// MARK: - Shared Building Blocks (matched to ZLT X28)

struct PageScroll<Content: View>: View {
    private let content: Content
    init(@ViewBuilder content: () -> Content) { self.content = content() }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                content
            }
            .padding(28)
            .frame(maxWidth: 740, alignment: .leading)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

struct PageHeader: View {
    let title: String
    let subtitle: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.system(size: 25, weight: .semibold, design: .rounded))
            Text(subtitle)
                .font(.callout)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct Card<Content: View>: View {
    private let content: Content
    init(@ViewBuilder content: () -> Content) { self.content = content() }

    var body: some View {
        content
            .padding(18)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Color(nsColor: .controlBackgroundColor))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .strokeBorder(Color.primary.opacity(0.07))
            )
    }
}

struct InfoBox: View {
    let title: String
    let text: String
    var icon: String = "info.circle"

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(Color.accentColor)
                .padding(.top, 2)
            VStack(alignment: .leading, spacing: 4) {
                Text(title).font(.callout.weight(.semibold))
                Text(text)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 0)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(Color.accentColor.opacity(0.07))
        )
    }
}

struct ScopeNote: View {
    let text: String
    init(_ text: String) { self.text = text }

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "checkmark.shield")
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(.secondary)
                .padding(.top, 2)
            Text(text)
                .font(.callout)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 2)
    }
}

struct ScopeRow: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label).font(.callout.weight(.medium))
            Text(value)
                .font(.callout)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
                .textSelection(.enabled)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct InfoRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text(label).foregroundStyle(.secondary)
            Spacer(minLength: 12)
            Text(value)
                .multilineTextAlignment(.trailing)
                .textSelection(.enabled)
        }
        .font(.callout)
    }
}

struct StatusDot: View {
    let ok: Bool
    var body: some View {
        Circle()
            .fill(ok ? Color.green : Color.secondary.opacity(0.45))
            .frame(width: 8, height: 8)
    }
}

struct Chip: View {
    let text: String
    var color: Color = .secondary

    var body: some View {
        Text(text)
            .font(.system(size: 11, weight: .semibold))
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .foregroundStyle(color)
            .background(Capsule().fill(color.opacity(0.14)))
    }
}

struct NoticeToast: View {
    let text: String
    let dismiss: () -> Void

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "info.circle.fill")
                .foregroundStyle(Color.accentColor)
            Text(text)
                .font(.callout)
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: 520, alignment: .leading)
            Button(action: dismiss) {
                Image(systemName: "xmark")
            }
            .buttonStyle(.borderless)
            .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .strokeBorder(Color.primary.opacity(0.1))
        )
        .shadow(color: .black.opacity(0.15), radius: 12, y: 4)
    }
}

struct StepCard<Content: View>: View {
    let number: Int
    let title: String
    let detail: String
    var done: Bool = false
    private let content: Content

    init(number: Int, title: String, detail: String, done: Bool = false, @ViewBuilder content: () -> Content) {
        self.number = number
        self.title = title
        self.detail = detail
        self.done = done
        self.content = content()
    }

    var body: some View {
        Card {
            HStack(alignment: .top, spacing: 14) {
                ZStack {
                    Circle()
                        .fill(done ? Color.green.opacity(0.18) : Color.secondary.opacity(0.12))
                        .frame(width: 30, height: 30)
                    if done {
                        Image(systemName: "checkmark")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundStyle(.green)
                    } else {
                        Text("\(number)")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundStyle(.secondary)
                    }
                }
                VStack(alignment: .leading, spacing: 10) {
                    Text(title).font(.headline)
                    Text(detail)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                    content
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }
}
