package com.pinky.dashboard

import androidx.compose.ui.graphics.Color
import com.pinky.dashboard.ui.screens.orders.parseOrderItemColor
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class OrderItemColorTest {
    @Test
    fun parsesSixDigitHexColorExactly() {
        assertEquals(Color(0xFFFF0000), parseOrderItemColor("#FF0000"))
    }

    @Test
    fun parsesShortHexColor() {
        assertEquals(Color(0xFF00FF00), parseOrderItemColor("#0F0"))
    }

    @Test
    fun parsesArgbHexColor() {
        assertEquals(Color(0x80112233), parseOrderItemColor("#80112233"))
    }

    @Test
    fun parsesArabicColorNames() {
        assertEquals(Color(0xFF2196F3), parseOrderItemColor("أزرق"))
    }

    @Test
    fun invalidColorDoesNotCrash() {
        assertNull(parseOrderItemColor("#12"))
    }
}
