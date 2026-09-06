package fr.atlasos.connect

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters

class AtlasSyncWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = try {
        HealthChangeSync(applicationContext).run()
        Result.success()
    } catch (_: SecurityException) {
        // Background Health Connect permission can be revoked independently.
        // Do not create an endless retry storm; foreground/manual sync remains.
        Result.success()
    } catch (_: Exception) {
        Result.retry()
    }
}
