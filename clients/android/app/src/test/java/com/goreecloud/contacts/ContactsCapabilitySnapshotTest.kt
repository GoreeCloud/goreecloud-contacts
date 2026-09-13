package com.goreecloud.contacts

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ContactsCapabilitySnapshotTest {
    @Test
    fun developmentShellDoesNotClaimRuntimeCapabilities() {
        val snapshot = ContactsCapabilitySnapshot.developmentShell()
        val capabilities = listOf(
            snapshot.identitySession,
            snapshot.cardDavRead,
            snapshot.cardDavWrite,
            snapshot.offlineCache,
            snapshot.backgroundSync,
            snapshot.androidContactsBridge,
        )

        assertEquals(6, capabilities.size)
        assertTrue(capabilities.all { it.state == ContactsCapabilityState.NOT_IMPLEMENTED })
        assertTrue(capabilities.none { it.state == ContactsCapabilityState.AVAILABLE })
    }

    @Test
    fun unavailableCapabilitiesExplainTheirState() {
        val snapshot = ContactsCapabilitySnapshot.developmentShell()

        assertTrue(snapshot.cardDavRead.explanation.isNotBlank())
        assertTrue(snapshot.androidContactsBridge.explanation.isNotBlank())
    }
}
