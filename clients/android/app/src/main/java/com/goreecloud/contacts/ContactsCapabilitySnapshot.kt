package com.goreecloud.contacts

enum class ContactsCapabilityState {
    NOT_IMPLEMENTED,
    UNAVAILABLE,
    AVAILABLE,
}

data class ContactsCapability(
    val state: ContactsCapabilityState,
    val explanation: String,
)

data class ContactsCapabilitySnapshot(
    val identitySession: ContactsCapability,
    val cardDavRead: ContactsCapability,
    val cardDavWrite: ContactsCapability,
    val offlineCache: ContactsCapability,
    val backgroundSync: ContactsCapability,
    val androidContactsBridge: ContactsCapability,
) {
    companion object {
        fun developmentShell(): ContactsCapabilitySnapshot {
            val pending = ContactsCapability(
                state = ContactsCapabilityState.NOT_IMPLEMENTED,
                explanation = "Not connected in the native Android Development shell",
            )
            return ContactsCapabilitySnapshot(
                identitySession = pending,
                cardDavRead = pending,
                cardDavWrite = pending,
                offlineCache = pending,
                backgroundSync = pending,
                androidContactsBridge = pending,
            )
        }
    }
}
