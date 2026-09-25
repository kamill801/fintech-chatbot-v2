import SwiftUI
import UIKit
import WebKit

private enum JangbuSite {
    static let home = URL(string: "https://jangbu-ai.vercel.app/")!

    static func staysInApp(_ url: URL) -> Bool {
        guard url.scheme == "https", let host = url.host?.lowercased() else { return false }
        return host == home.host || host == "kakao.com" || host.hasSuffix(".kakao.com")
            || host == "daum.net" || host.hasSuffix(".daum.net")
    }
}

@MainActor
private final class BrowserState: ObservableObject {
    @Published var isLoading = true
    @Published var hasConnectionError = false
    weak var webView: WKWebView?

    func retry() {
        hasConnectionError = false
        isLoading = true
        webView?.load(URLRequest(url: JangbuSite.home, cachePolicy: .reloadIgnoringLocalCacheData))
    }
}

struct WebContentView: View {
    @StateObject private var browser = BrowserState()

    var body: some View {
        ZStack {
            Color(red: 246 / 255, green: 243 / 255, blue: 236 / 255)
                .ignoresSafeArea()

            JangbuWebView(browser: browser)

            if browser.isLoading && !browser.hasConnectionError {
                ProgressView()
                    .tint(Color(red: 11 / 255, green: 113 / 255, blue: 217 / 255))
                    .accessibilityLabel("장부 AI 불러오는 중")
            }

            if browser.hasConnectionError {
                VStack(spacing: 16) {
                    Text("장부 AI에 연결할 수 없어요")
                        .font(.headline)
                    Text("인터넷 연결을 확인한 뒤 다시 시도해 주세요.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    Button("다시 연결", action: browser.retry)
                        .buttonStyle(.borderedProminent)
                }
                .padding(24)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(Color(red: 246 / 255, green: 243 / 255, blue: 236 / 255))
            }
        }
    }
}

private struct JangbuWebView: UIViewRepresentable {
    @ObservedObject var browser: BrowserState

    func makeCoordinator() -> Coordinator { Coordinator(browser: browser) }

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true
        webView.scrollView.contentInsetAdjustmentBehavior = .automatic
        browser.webView = webView
        webView.load(URLRequest(url: JangbuSite.home))
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {}

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate {
        private let browser: BrowserState

        init(browser: BrowserState) { self.browser = browser }

        func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
            browser.isLoading = true
            browser.hasConnectionError = false
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            browser.isLoading = false
            browser.hasConnectionError = false
        }

        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            guard (error as NSError).code != NSURLErrorCancelled else { return }
            browser.isLoading = false
            browser.hasConnectionError = true
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            guard (error as NSError).code != NSURLErrorCancelled else { return }
            browser.isLoading = false
            browser.hasConnectionError = true
        }

        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
        ) {
            guard let url = navigationAction.request.url else {
                decisionHandler(.cancel)
                return
            }
            if JangbuSite.staysInApp(url) || url.scheme == "about" {
                decisionHandler(.allow)
            } else {
                UIApplication.shared.open(url)
                decisionHandler(.cancel)
            }
        }

        func webView(
            _ webView: WKWebView,
            createWebViewWith configuration: WKWebViewConfiguration,
            for navigationAction: WKNavigationAction,
            windowFeatures: WKWindowFeatures
        ) -> WKWebView? {
            if navigationAction.targetFrame == nil, let url = navigationAction.request.url {
                if JangbuSite.staysInApp(url) {
                    webView.load(navigationAction.request)
                } else {
                    UIApplication.shared.open(url)
                }
            }
            return nil
        }
    }
}
