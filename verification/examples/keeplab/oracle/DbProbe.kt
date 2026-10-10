package com.keeplab.app.benchmark

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import dev.androidstack.verification.VerificationEnv
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Reference separate oracle for engines that cannot read the database themselves (Maestro).
 * Driven as `am instrument -e class ...DbProbe -e journey J1`.
 */
@RunWith(AndroidJUnit4::class)
class DbProbe {

    @Test
    fun verifyDb() {
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        val journey = VerificationEnv.journey()
        val result = Verifier.write(ctx, journey)
        val outcome = result.getString("outcome")
        println("VERIFY_OUTCOME=$outcome")
        assertEquals("DB oracle for $journey", "PASS", outcome)
    }
}
