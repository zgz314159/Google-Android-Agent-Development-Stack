package com.keeplab.app.benchmark

import android.content.Context
import androidx.room.Room
import com.keeplab.app.data.local.KeepLabDatabase
import com.keeplab.app.data.local.NoteWithDetails
import dev.androidstack.verification.VerificationEnv
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Reference project oracle. Both engines call this same code so the terminal PASS/FAIL
 * decision is identical. It asserts real database state — never "the UI looked right" — and
 * writes `verify-part.json` into the bench dir, exactly the file the host consumes.
 */
object Verifier {

    private data class Check(val name: String, val expected: String, val actual: String, val pass: Boolean) {
        fun toJson(): JSONObject = JSONObject()
            .put("name", name).put("expected", expected).put("actual", actual).put("pass", pass)
    }

    fun write(context: Context, journey: String): JSONObject {
        val result = verify(context, journey)
        File(VerificationEnv.outDir(context), "verify-part.json").writeText(result.toString(2))
        return result
    }

    fun verify(context: Context, journey: String): JSONObject {
        val db = Room.databaseBuilder(context, KeepLabDatabase::class.java, "keeplab.db").build()
        val rows: List<NoteWithDetails> = try {
            runBlocking { db.noteDao().observeAll().first() }
        } finally {
            db.close()
        }
        val checks = when (journey) {
            "J1" -> j1(rows)
            else -> listOf(Check("journey-known", "J1", journey, false))
        }
        val outcome = if (checks.all { it.pass }) "PASS" else "FAIL"
        return JSONObject()
            .put("journey", journey)
            .put("outcome", outcome)
            .put("timestamp_ms", System.currentTimeMillis())
            .put("database", JSONObject()
                .put("checked", true)
                .put("note_count", rows.size)
                .put("checks", JSONArray(checks.map { it.toJson() })))
    }

    private fun j1(rows: List<NoteWithDetails>): List<Check> {
        val n = rows.firstOrNull { it.note.title == "VC-J1-Title" }
        return listOf(
            Check("note-exists", "VC-J1-Title present", if (n != null) "present" else "missing", n != null),
            Check("body-edited", "VC-J1-Body-Edited", n?.note?.body ?: "", n?.note?.body == "VC-J1-Body-Edited"),
            Check("not-archived", "false", "${n?.note?.archived}", n?.note?.archived == false),
            Check("not-trashed", "false", "${n?.note?.trashed}", n?.note?.trashed == false),
        )
    }
}
