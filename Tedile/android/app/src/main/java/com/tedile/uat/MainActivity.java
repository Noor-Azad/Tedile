package com.tedile.uat;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import android.webkit.ConsoleMessage;
import android.webkit.GeolocationPermissions;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {

    private static final String UAT_URL = "https://tedile-uat.onrender.com";
    private static final String DEBUG_URL = "http://10.0.2.2:5001";
    private static final int PERMISSIONS = 42;
    private static final int FILE_CHOOSER = 43;

    private WebView webView;
    private ValueCallback<Uri[]> fileCallback;

    @Override
    public void onCreate(Bundle state) {
        super.onCreate(state);

        webView = new WebView(this);
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);

        // Required for navigator.geolocation in the WebView
        settings.setGeolocationEnabled(true);

        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);

        webView.setWebViewClient(new WebViewClient() {

            @Override
            public void onPageStarted(
                    WebView view,
                    String url,
                    android.graphics.Bitmap favicon) {

                Log.d("TedileWebView", "Page URL loaded: " + url);

                super.onPageStarted(view, url, favicon);
            }

            @Override
            public void onPageFinished(WebView view, String url) {

                Log.d("TedileWebView", "onPageFinished: " + url);

                super.onPageFinished(view, url);
            }

            @Override
            public boolean shouldOverrideUrlLoading(
                    WebView view,
                    WebResourceRequest request) {

                Uri url = request.getUrl();
                String scheme = url.getScheme();

                Log.d("TedileWebView",
                        "URL INTERCEPTED: " + url);

                // Normal web pages stay inside Tedile
                if ("http".equals(scheme) || "https".equals(scheme)) {
                    view.loadUrl(url.toString());
                    return true;
                }

                // Handle Android intent:// URLs
                if ("intent".equals(scheme)) {
                    try {
                        Intent intent = Intent.parseUri(
                                url.toString(),
                                Intent.URI_INTENT_SCHEME
                        );

                        if (intent.resolveActivity(getPackageManager()) != null) {
                            startActivity(intent);
                        } else {
                            String fallbackUrl =
                                    intent.getStringExtra(
                                            "browser_fallback_url"
                                    );

                            if (fallbackUrl != null) {
                                view.loadUrl(fallbackUrl);
                            }
                        }

                    } catch (Exception e) {
                        Log.e(
                                "TedileWebView",
                                "Unable to open intent URL: " + url,
                                e
                        );
                    }

                    return true;
                }

                // Other external schemes
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW, url);

                    if (intent.resolveActivity(getPackageManager()) != null) {
                        startActivity(intent);
                    }

                } catch (Exception e) {
                    Log.e(
                            "TedileWebView",
                            "Unable to open external URL: " + url,
                            e
                    );
                }

                return true;
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {

            @Override
            public boolean onConsoleMessage(
                    ConsoleMessage consoleMessage) {

                Log.d(
                        "TedileWebView",
                        consoleMessage.message()
                );

                return true;
            }

            @Override
            public void onGeolocationPermissionsShowPrompt(
                    String origin,
                    GeolocationPermissions.Callback callback) {

                Log.d(
                        "TedileWebView",
                        "GEOLOCATION PERMISSION REQUEST: " + origin
                );

                if (checkSelfPermission(
                        Manifest.permission.ACCESS_FINE_LOCATION
                ) == PackageManager.PERMISSION_GRANTED
                        || checkSelfPermission(
                        Manifest.permission.ACCESS_COARSE_LOCATION
                ) == PackageManager.PERMISSION_GRANTED) {

                    Log.d(
                            "TedileWebView",
                            "GEOLOCATION PERMISSION GRANTED"
                    );

                    callback.invoke(origin, true, false);

                } else {

                    Log.d(
                            "TedileWebView",
                            "GEOLOCATION PERMISSION DENIED"
                    );

                    callback.invoke(origin, false, false);
                }
            }

            @Override
            public boolean onShowFileChooser(
                    WebView view,
                    ValueCallback<Uri[]> callback,
                    FileChooserParams params) {

                if (fileCallback != null) {
                    fileCallback.onReceiveValue(null);
                }

                fileCallback = callback;

                startActivityForResult(
                        params.createIntent(),
                        FILE_CHOOSER
                );

                return true;
            }
        });

        // Request Android permissions
        if (needsPermissions()) {

            requestPermissions(
                    new String[]{
                            Manifest.permission.ACCESS_FINE_LOCATION,
                            Manifest.permission.ACCESS_COARSE_LOCATION,
                            Manifest.permission.CAMERA,
                            permissionForMedia()
                    },
                    PERMISSIONS
            );
        }

        boolean isDebuggable = (getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0;
        String startUrl = isDebuggable ? DEBUG_URL : UAT_URL;
        Log.d(
                "TedileWebView",
                "webView.loadUrl: " + startUrl
        );

        webView.loadUrl(startUrl);
    }

    private String permissionForMedia() {

        return android.os.Build.VERSION.SDK_INT >= 33
                ? Manifest.permission.READ_MEDIA_IMAGES
                : Manifest.permission.READ_EXTERNAL_STORAGE;
    }

    private boolean needsPermissions() {

        return checkSelfPermission(
                Manifest.permission.ACCESS_COARSE_LOCATION
        ) != PackageManager.PERMISSION_GRANTED

                || checkSelfPermission(
                Manifest.permission.CAMERA
        ) != PackageManager.PERMISSION_GRANTED;
    }

    @Override
    protected void onActivityResult(
            int request,
            int result,
            Intent data) {

        super.onActivityResult(request, result, data);

        if (request == FILE_CHOOSER
                && fileCallback != null) {

            fileCallback.onReceiveValue(
                    WebChromeClient.FileChooserParams
                            .parseResult(result, data)
            );

            fileCallback = null;
        }
    }

    @Override
    public void onBackPressed() {

        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
