package com.keeplab.app.benchmark

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.keeplab.app.data.local.KeepLabDatabase
import com.keeplab.app.data.local.NoteEntity
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Reference fixture seeder: writes the *real* database directly through Room so test data is
 * never created by UI taps. Run as a separate `am instrument` invocation before the measured
 * journey; its wall time is setup, never mixed into T7.
 */
@RunWith(AndroidJUnit4::class)
class FixtureSeeder {

    private val context: Context get() = ApplicationProvider.getApplicationContext()

    private fun note(title: String, body: String = "") = NoteEntity(
        kind = "TEXT", title = title, body = body, color = "default",
        pinned = false, archived = false, trashed = false, createdAt = 1L, updatedAt = 1L,
    )

    private fun reset() {
        context.deleteDatabase("keeplab.db")
        context.getSharedPreferences("keeplab_prefs", Context.MODE_PRIVATE).edit().clear().commit()
    }

    private fun open(): KeepLabDatabase =
        Room.databaseBuilder(context, KeepLabDatabase::class.java, "keeplab.db").build()

    @Test
    fun seedJ1() = runBlocking {
        reset()
        val db = open()
        db.noteDao().observeAll().first()
        db.close()
        println("SEED_J1_OK")
    }
}
