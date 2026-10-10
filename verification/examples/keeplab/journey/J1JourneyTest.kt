package com.keeplab.app.benchmark

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.uiautomator.By
import dev.androidstack.verification.FailureBundleRule
import dev.androidstack.verification.JourneyBase
import dev.androidstack.verification.TimingLogger
import dev.androidstack.verification.UiDriver
import dev.androidstack.verification.VerificationEnv
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Reference journey, migrated to the Verification Layer device-side support sources
 * (android/uiautomator). Engine: uiautomator. The app package is injected, never hardcoded.
 */
@RunWith(AndroidJUnit4::class)
class J1JourneyTest : JourneyBase() {

    private val ui = UiDriver(appPackage)

    @get:Rule
    val failureBundle = FailureBundleRule { Verifier.verify(ctx, VerificationEnv.journey()) }

    @Test
    fun j1ComposeCrud() {
        TimingLogger.begin(ctx, VerificationEnv.runId(), VerificationEnv.journey())

        action("launch") { ui.launchApp(device, ctx, By.text("KeepLab")) }

        action("create-note") {
            ui.clickDesc(device, "New text note")
            ui.waitFor(device, By.desc("Back"))
            ui.type(device, 0, "VC-J1-Title")
            ui.type(device, 1, "VC-J1-Body")
            settle()
        }

        action("back-home") {
            ui.clickDesc(device, "Back")
            ui.waitFor(device, By.text("KeepLab"))
        }

        action("search") {
            ui.clickDesc(device, "Search")
            ui.type(device, 0, "VC-J1-Title")
        }

        action("open-note") {
            ui.waitFor(device, By.text("VC-J1-Title"))
            ui.clickText(device, "VC-J1-Title")
        }

        action("edit-body") {
            ui.waitFor(device, By.desc("Back"))
            ui.type(device, 1, "VC-J1-Body-Edited")
            settle()
        }

        action("back-home-final") {
            ui.clickDesc(device, "Back")
            ui.waitFor(device, By.text("KeepLab"))
        }

        val result = verify()
        TimingLogger.runEnd()
        assertEquals("J1 oracle: $result", "PASS", result.getString("outcome"))
    }

    override fun verify() = Verifier.write(ctx, VerificationEnv.journey())
}
