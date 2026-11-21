package com.pinky.dashboard

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.pinky.dashboard.data.local.PinkyDatabase
import com.pinky.dashboard.data.local.SessionCacheCleaner
import com.pinky.dashboard.data.local.entity.*
import com.pinky.dashboard.core.sync.OrderSyncManager
import com.pinky.dashboard.domain.model.Order
import com.pinky.dashboard.domain.model.OrderStatus
import com.pinky.dashboard.domain.repository.OrderRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.emptyFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class SessionCacheIsolationTest {
    private lateinit var database: PinkyDatabase

    @Before
    fun setUp() {
        database = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext<Context>(),
            PinkyDatabase::class.java
        ).allowMainThreadQueries().build()
    }

    @After
    fun tearDown() {
        database.close()
    }

    @Test
    fun clearRemovesEveryCachedTableAndKeepsTheRoomSchemaUsable() = runBlocking {
        val now = System.currentTimeMillis()
        database.orderDao().insertOrder(
            OrderEntity("order-1", "EL-1", "Customer", "01000000000", "Address", "Cairo", "Center", 100.0, 10.0, 0.0, 110.0, "cod", "pending", "new", now, "note")
        )
        database.orderDao().insertOrderItems(
            listOf(OrderItemEntity("item-1", "order-1", "product-1", "Product", null, null, null, 1, 100.0, 100.0, null))
        )
        val product = ProductEntity("product-1", "Product", "Description", "image", "[]", "category-1", "Category", 100.0, null, null, null, "SKU-1", 2, "[]", "[]", true, false, now)
        database.productDao().insertProduct(product)
        database.categoryDao().insertCategory(CategoryEntity("category-1", "Category", "image", 1, true, 1))
        database.offerDao().insertOffer(OfferEntity("offer-1", "Offer", "Description", "10%", "image", "Shop", null, null, 1, true, now, now + 60_000L))
        database.customerDao().insertCustomer(CustomerEntity("customer-1", "Customer", "01000000000", null, "Address", "Cairo", 1, 110.0, now, now))
        database.shippingDao().insertGovernorate(ShippingGovernorateEntity("gov-1", "Cairo", 10.0, "2 days", true))
        database.shippingDao().insertCenter(ShippingCenterEntity("center-1", "gov-1", "Center", 10.0, null, true))

        SessionCacheCleaner(database).clear()

        assertTrue(database.orderDao().getAllOrdersFlow().first().isEmpty())
        assertTrue(database.orderDao().getItemsForOrders(listOf("order-1")).isEmpty())
        assertTrue(database.productDao().getAllProductsFlow().first().isEmpty())
        assertTrue(database.categoryDao().getAllCategoriesOnce().isEmpty())
        assertTrue(database.offerDao().getAllOffersFlow().first().isEmpty())
        assertTrue(database.customerDao().getAllCustomersFlow().first().isEmpty())
        assertTrue(database.shippingDao().getAllGovernoratesFlow().first().isEmpty())
        assertTrue(database.shippingDao().getAllCentersFlow().first().isEmpty())

        database.productDao().insertProduct(product.copy(id = "product-after-clear"))
        assertNotNull(database.productDao().getProductById("product-after-clear"))
        assertEquals(1, database.productDao().getAllProductsFlow().first().size)
    }

    @Test
    fun syncManagerRejectsReadsOutsideAnActiveSession() = runBlocking {
        var syncCalls = 0
        val repository = object : OrderRepository {
            override suspend fun clearLocalOrders() = Unit
            override fun getOrdersFlow(): Flow<List<Order>> = emptyFlow()
            override suspend fun getOrderById(orderId: String): Order? = null
            override suspend fun updateOrderStatus(orderId: String, newStatus: OrderStatus, note: String?): Result<Order> =
                Result.failure(UnsupportedOperationException())
            override suspend fun syncOrders(): Result<Unit> {
                syncCalls += 1
                return Result.success(Unit)
            }
            override suspend fun addOrder(order: Order): Result<Order> = Result.failure(UnsupportedOperationException())
        }
        val manager = OrderSyncManager(ApplicationProvider.getApplicationContext(), repository)
        try {
            assertTrue(manager.performSync().isFailure)
            assertEquals(0, syncCalls)

            manager.startPeriodicSync()
            assertTrue(manager.performSync().isSuccess)
            assertEquals(1, syncCalls)

            manager.stopPeriodicSync()
            assertTrue(manager.performSync().isFailure)
            assertEquals(1, syncCalls)
        } finally {
            manager.stopPeriodicSync()
            manager.destroy()
        }
    }
}
