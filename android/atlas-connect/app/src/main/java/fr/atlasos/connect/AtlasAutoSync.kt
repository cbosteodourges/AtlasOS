package fr.atlasos.connect

import android.content.ContentProvider
import android.content.ContentValues
import android.database.Cursor
import android.net.Uri
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

/**
 * Starts Atlas' Health Connect background pipeline as soon as the app process
 * is created. This deliberately lives outside MainActivity so automatic sync
 * does not depend on the user opening the Atlas Connect screen.
 */
object AtlasAutoSync {
    const val UNIQUE_WORK = "atlas-health-sync"

    fun schedule(context: android.content.Context) {
        val prefs = context.getSharedPreferences("atlas", android.content.Context.MODE_PRIVATE)
        if (!prefs.contains("token") || prefs.getString("server", "").isNullOrBlank()) return

        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()
        val request = PeriodicWorkRequestBuilder<AtlasSyncWorker>(1, TimeUnit.HOURS)
            .setConstraints(constraints)
            .build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            UNIQUE_WORK,
            ExistingPeriodicWorkPolicy.UPDATE,
            request,
        )
    }
}

/**
 * Zero-UI initializer. Android instantiates this provider when Atlas Connect's
 * process starts, which is enough to restore the periodic job after an update
 * or a normal application launch.
 */
class AtlasAutoSyncInitializer : ContentProvider() {
    override fun onCreate(): Boolean {
        context?.let(AtlasAutoSync::schedule)
        return true
    }
    override fun query(uri: Uri, projection: Array<out String>?, selection: String?, selectionArgs: Array<out String>?, sortOrder: String?): Cursor? = null
    override fun getType(uri: Uri): String? = null
    override fun insert(uri: Uri, values: ContentValues?): Uri? = null
    override fun delete(uri: Uri, selection: String?, selectionArgs: Array<out String>?): Int = 0
    override fun update(uri: Uri, values: ContentValues?, selection: String?, selectionArgs: Array<out String>?): Int = 0
}
