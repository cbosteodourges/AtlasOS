package fr.atlasos.connect

import android.annotation.SuppressLint
import android.content.Intent
import android.os.Bundle
import android.view.Gravity
import android.view.Menu
import android.view.MenuItem
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.ComponentActivity

class AtlasWebActivity : ComponentActivity() {
    companion object { private const val SETTINGS_ID = 1001; private const val REFRESH_ID = 1002 }
    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        title = "Atlas"
        webView = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.databaseEnabled = true
            settings.allowFileAccess = false
            settings.allowContentAccess = false
            webChromeClient = WebChromeClient()
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean = false
                override fun onReceivedError(view: WebView?, request: WebResourceRequest?, error: android.webkit.WebResourceError?) {
                    if (request?.isForMainFrame == true) Toast.makeText(this@AtlasWebActivity, "Atlas OS indisponible. Les données Santé Connect resteront en attente.", Toast.LENGTH_LONG).show()
                }
            }
        }
        setContentView(webView)
        loadAtlas()
    }

    private fun atlasUrl(): String {
        val prefs = getSharedPreferences("atlas", MODE_PRIVATE)
        val server = AtlasTransport.normalizeServer(prefs.getString("server", "").orEmpty())
        return "$server/app/atlas-cockpit.html"
    }
    private fun loadAtlas() = try { webView.loadUrl(atlasUrl()) } catch (_: Exception) {
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menu.add(Menu.NONE, REFRESH_ID, 0, "Actualiser").setShowAsAction(MenuItem.SHOW_AS_ACTION_IF_ROOM)
        menu.add(Menu.NONE, SETTINGS_ID, 1, "Atlas Connect / Santé Connect").setShowAsAction(MenuItem.SHOW_AS_ACTION_IF_ROOM)
        return true
    }
    override fun onOptionsItemSelected(item: MenuItem): Boolean = when (item.itemId) {
        REFRESH_ID -> { webView.reload(); true }
        SETTINGS_ID -> { startActivity(Intent(this, MainActivity::class.java)); true }
        else -> super.onOptionsItemSelected(item)
    }
    @Deprecated("Deprecated in Java")
    override fun onBackPressed() { if (::webView.isInitialized && webView.canGoBack()) webView.goBack() else super.onBackPressed() }
}
