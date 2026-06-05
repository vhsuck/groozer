package com.groozy.app

import android.annotation.SuppressLint
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.webkit.*
import android.widget.ProgressBar
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout

/**
 * Groozy Android App
 * WebView-обёртка для веб-приложения Groozy
 *
 * Функции:
 * - WebView с поддержкой JavaScript
 * - Pull-to-refresh (SwipeRefreshLayout)
 * - Прогресс загрузки страницы
 * - Обработка кнопки «Назад»
 * - Кэширование для офлайн-работы
 * - Перехват внешних ссылок в браузер
 */
class MainActivity : AppCompatActivity() {

    companion object {
        // Замените на URL вашего сервера
        const val BASE_URL = "http://10.0.2.2:8000"  // Android эмулятор → localhost
        // const val BASE_URL = "https://your-domain.com"  // Продакшен
    }

    private lateinit var webView: WebView
    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var progressBar: ProgressBar

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)
        swipeRefresh = findViewById(R.id.swipeRefresh)
        progressBar = findViewById(R.id.progressBar)

        setupWebView()
        setupSwipeRefresh()
        setupBackButton()

        // Восстановление состояния при повороте экрана
        if (savedInstanceState != null) {
            webView.restoreState(savedInstanceState)
        } else {
            webView.loadUrl(BASE_URL)
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        webView.settings.apply {
            // JavaScript включён — требуется для SPA
            javaScriptEnabled = true

            // DOM Storage (для localStorage токена)
            domStorageEnabled = true

            // Кэширование
            cacheMode = WebSettings.LOAD_DEFAULT

            // Масштабирование
            builtInZoomControls = false
            displayZoomControls = false
            setSupportZoom(false)

            // Адаптивная вёрстка
            useWideViewPort = true
            loadWithOverviewMode = true

            // Медиа
            mediaPlaybackRequiresUserGesture = false

            // Геолокация
            setGeolocationEnabled(true)

            // Файловый доступ (для загрузки документов)
            allowFileAccess = true
        }

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView?,
                request: WebResourceRequest?
            ): Boolean {
                val url = request?.url?.toString() ?: return false

                // Внешние ссылки открываем в браузере
                return if (!url.startsWith(BASE_URL)) {
                    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                    true
                } else {
                    false
                }
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                swipeRefresh.isRefreshing = false
                progressBar.visibility = View.GONE
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                super.onReceivedError(view, request, error)
                // Показать офлайн-страницу
                if (request?.isForMainFrame == true) {
                    view?.loadUrl("file:///android_asset/offline.html")
                }
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                progressBar.progress = newProgress
                progressBar.visibility = if (newProgress < 100) View.VISIBLE else View.GONE
            }

            // Разрешения геолокации
            override fun onGeolocationPermissionsShowPrompt(
                origin: String?,
                callback: GeolocationPermissions.Callback?
            ) {
                callback?.invoke(origin, true, false)
            }

            // Загрузка файлов
            override fun onShowFileChooser(
                webView: WebView?,
                filePathCallback: ValueCallback<Array<Uri>>?,
                fileChooserParams: FileChooserParams?
            ): Boolean {
                val intent = fileChooserParams?.createIntent() ?: return false
                fileUploadCallback = filePathCallback
                try {
                    filePickerLauncher.launch(intent)
                } catch (e: Exception) {
                    fileUploadCallback = null
                    return false
                }
                return true
            }
        }
    }

    private var fileUploadCallback: ValueCallback<Array<Uri>>? = null

    private val filePickerLauncher =
        registerForActivityResult(androidx.activity.result.contract.ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == RESULT_OK) {
                fileUploadCallback?.onReceiveValue(
                    WebChromeClient.FileChooserParams.parseResult(result.resultCode, result.data)
                )
            } else {
                fileUploadCallback?.onReceiveValue(null)
            }
            fileUploadCallback = null
        }

    private fun setupSwipeRefresh() {
        swipeRefresh.setColorSchemeColors(
            getColor(android.R.color.holo_orange_light)
        )
        swipeRefresh.setOnRefreshListener {
            webView.reload()
        }
    }

    private fun setupBackButton() {
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (webView.canGoBack()) {
                    webView.goBack()
                } else {
                    finish()
                }
            }
        })
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        webView.saveState(outState)
    }

    override fun onPause() {
        super.onPause()
        webView.onPause()
    }

    override fun onResume() {
        super.onResume()
        webView.onResume()
    }

    override fun onDestroy() {
        webView.destroy()
        super.onDestroy()
    }
}
