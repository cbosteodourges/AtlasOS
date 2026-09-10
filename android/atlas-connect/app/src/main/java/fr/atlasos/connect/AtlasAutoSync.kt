package fr.atlasos.connect

import android.content.ContentProvider
import android.content.ContentValues
import android.database.Cursor
import android.net.Uri
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

/** Central scheduler for the Health Connect -> Atlas pipeline. */
object AtlasAutoSync {
    // Deliberately different from the legacy name cancelled by MainActivity.
    // This lets us test auto-sync without changing the stable manual path.
    const val PERIODIC_WORK = "atlas-health-auto-sync-v2"
    const val LAUNCH_WORK = "atlas-health-launch-sync-v2"

    fun schedule(context: android.content.Context) {
        val prefs = context.getSharedPreferences("atlas", android.content.Context.MODE_PRIVATE)
        if (!prefs.contains("token") || prefs.getString("server", "").isNullOrBlank()) return

        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()
        val manager = WorkManager.getInstance(context)

        // Fast catch-up whenever Atlas Connect's process starts. This normally
        // runs while the application is foregrounded, so ordinary HC read
        // permission is sufficient.
        manager.enqueueUniqueWork(
            LAUNCH_WORK,
            ExistingWorkPolicy.REPLACE,
            OneTimeWorkRequestBuilder<AtlasSyncWorker>()
                .setConstraints(constraints)
                .build(),
        )

        // Background freshness between launches. Fifteen minutes is the
        // minimum cadence accepted by WorkManager. Android may defer an
        // execution, while the differential sender keeps each attempt light.
        manager.enqueueUniquePeriodicWork(
            PERIODIC_WORK,
            ExistingPeriodicWorkPolicy.UPDATE,
            PeriodicWorkRequestBuilder<AtlasSyncWorker>(15, TimeUnit.MINUTES)
                .setConstraints(constraints)
                .build(),
        )
    }
}

/**
 * Zero-UI initializer. Android instantiates providers before MainActivity,
 * making opening Atlas enough to trigger a catch-up without another button.
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
