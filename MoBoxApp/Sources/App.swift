import SwiftUI
import AppKit

@main
enum MoBoxMain {
    static var delegate: AppDelegate?

    @MainActor
    static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        MoBoxMain.delegate = delegate
        app.delegate = delegate
        app.run()
    }
}

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate, NSMenuDelegate {
    private let model = AppModel.shared
    private var window: NSWindow?
    private var statusItem: NSStatusItem!

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        model.startBackendIfNeeded()
        buildMenuBar()
        buildWindow()
        NSApp.activate(ignoringOtherApps: true)

        Task {
            await model.refresh(forceScan: true)
            await model.checkForUpdate()
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        model.stopBackend()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        false
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        showWindow()
        return true
    }

    private func buildWindow() {
        let root = RootView().environmentObject(model)
        let controller = NSHostingController(rootView: root)
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 980, height: 680),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "MoBox"
        window.contentViewController = controller
        window.minSize = NSSize(width: 880, height: 580)
        window.setFrameAutosaveName("MoBoxMainWindow")
        window.center()
        window.delegate = self
        window.isReleasedWhenClosed = false
        self.window = window
        window.makeKeyAndOrderFront(nil)
    }

    @objc private func showWindow() {
        if window == nil { buildWindow() }
        window?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func buildMenuBar() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        let menu = NSMenu()
        menu.delegate = self
        statusItem.menu = menu
        if let image = NSImage(systemSymbolName: "tv.and.mediabox", accessibilityDescription: "MoBox") {
            image.isTemplate = true
            statusItem.button?.image = image
        }
    }

    func menuNeedsUpdate(_ menu: NSMenu) {
        menu.removeAllItems()
        let titleText: String
        if let fw = model.status.firmware, model.status.connected {
            titleText = "\(fw.model)Connected (\(model.status.serial ?? ""))"
        } else {
            titleText = "Mi Box not connected"
        }
        let head = NSMenuItem(title: titleText, action: nil, keyEquivalent: "")
        head.isEnabled = false
        menu.addItem(head)

        let phoneItem = NSMenuItem(title: "Phone Web App: \(model.phoneWebURL)", action: #selector(openPhoneWeb), keyEquivalent: "")
        phoneItem.target = self
        menu.addItem(phoneItem)
        menu.addItem(.separator())

        let setupItem = NSMenuItem(title: "Set Up My Mi Box (All-in-One)", action: #selector(runSimple), keyEquivalent: "")
        setupItem.target = self
        setupItem.isEnabled = model.status.connected && !model.status.busy
        menu.addItem(setupItem)

        let slideItem = NSMenuItem(title: "Start 4K Space & Nature Slideshow", action: #selector(startSlideshow), keyEquivalent: "")
        slideItem.target = self
        slideItem.isEnabled = model.status.connected
        menu.addItem(slideItem)

        let btItem = NSMenuItem(title: "Pair Apple Magic Mouse on TV", action: #selector(openBT), keyEquivalent: "")
        btItem.target = self
        btItem.isEnabled = model.status.connected
        menu.addItem(btItem)

        menu.addItem(.separator())
        let openItem = NSMenuItem(title: "Open MoBox", action: #selector(showWindow), keyEquivalent: "o")
        openItem.target = self
        menu.addItem(openItem)

        let updItem = NSMenuItem(title: "Check for Updates…", action: #selector(checkUpdates), keyEquivalent: "")
        updItem.target = self
        menu.addItem(updItem)

        let credit = NSMenuItem(title: "Made by Morad", action: nil, keyEquivalent: "")
        credit.isEnabled = false
        menu.addItem(credit)

        let quitItem = NSMenuItem(title: "Quit MoBox", action: #selector(quitApp), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)
    }

    @objc private func openPhoneWeb() {
        if let url = URL(string: model.phoneWebURL) {
            NSWorkspace.shared.open(url)
        }
    }

    @objc private func runSimple() {
        showWindow()
        Task { await model.runSimpleSetup() }
    }

    @objc private func startSlideshow() {
        Task { await model.performAction("slideshow") }
    }

    @objc private func openBT() {
        Task { await model.performAction("bluetooth") }
    }

    @objc private func checkUpdates() {
        Task { await model.checkForUpdate() }
    }

    @objc private func quitApp() {
        NSApp.terminate(nil)
    }
}
