from django.test import TestCase

from order.models import NEW_STATUS_CANCELLED
from order.models import NEW_STATUS_COMPLETE
from order.models import Order
from order.models import OrderStatus


class TestQuery(TestCase):
    def setUp(self):
        self.order1 = Order.objects.create()
        self.order2 = Order.objects.create()
        self.order3 = Order.objects.create()

    def test_query_cancelled_order(self):
        OrderStatus.objects.create(order=self.order1, status='Pending')
        OrderStatus.objects.create(order=self.order1, status='Cancelled')

        OrderStatus.objects.create(order=self.order2, status='Cancelled')
        OrderStatus.objects.create(order=self.order2, status='Complete')

        OrderStatus.objects.create(order=self.order3, status='Cancelled')

        orders = Order.objects.get_cancelled_orders()

        self.assert_orders_correct(orders)

    def test_query_new_cancelled_order(self):
        self.order1.status = NEW_STATUS_CANCELLED
        self.order2.status = NEW_STATUS_COMPLETE
        self.order3.status = NEW_STATUS_CANCELLED
        self.order1.save()
        self.order2.save()
        self.order3.save()

        orders = Order.objects.get_new_cancelled_orders()

        self.assert_orders_correct(orders)

    def assert_orders_correct(self, orders):
        self.assertEqual(orders.count(), 2)
        self.assertEqual(orders[0], self.order1)
        self.assertEqual(orders[1], self.order3)
