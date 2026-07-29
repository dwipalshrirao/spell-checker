import Cocoa
import SwiftUI

class AppDelegate: NSObject, NSApplicationDelegate, NSPopoverDelegate {
    private var statusItem: NSStatusItem!
    private var popover: NSPopover!
    private var viewModel: GrammarViewModel!

    func applicationDidFinishLaunching(_ notification: Notification) {
        viewModel = GrammarViewModel()
        setupStatusItem()
        setupPopover()
        checkHealthOnce()
    }

    private func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        guard let button = statusItem.button else { return }
        button.image = NSImage(systemSymbolName: "text.badge.checkmark", accessibilityDescription: "GrammarCheck")
        button.action = #selector(buttonClicked)
        button.target = self
    }

    private func setupPopover() {
        let contentView = PopoverContentView(viewModel: viewModel)
        let hostingController = NSHostingController(rootView: contentView)
        popover = NSPopover()
        popover.contentViewController = hostingController
        popover.behavior = .transient
        popover.contentSize = NSSize(width: 380, height: 600)
        popover.delegate = self
    }

    @objc @MainActor func buttonClicked() {
        guard let button = statusItem.button else { return }
        if popover.isShown {
            viewModel.isPopoverVisible = false
            popover.performClose(nil)
        } else {
            viewModel.isPopoverVisible = true
            popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
            popover.contentViewController?.view.window?.makeKey()
        }
    }

    func popoverDidClose(_ notification: Notification) {
        MainActor.assumeIsolated { viewModel.isPopoverVisible = false }
    }

    private func checkHealthOnce() {
        Task { @MainActor in
            await viewModel.checkHealth()
        }
    }
}
