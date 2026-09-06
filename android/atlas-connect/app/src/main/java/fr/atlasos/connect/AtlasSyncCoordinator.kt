package fr.atlasos.connect

import android.content.Context
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/** One process-wide gate for foreground, manual and WorkManager syncs. */
object AtlasSyncCoordinator {
    private val mutex = Mutex()

    suspend fun run(
        context: Context,
        onProgress: (Int, String) -> Unit = { _, _ -> },
    ): Int = mutex.withLock {
        HealthChangeSync(context.applicationContext).run(onProgress)
    }
}
