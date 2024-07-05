from django.core.management import BaseCommand

from order.models import Order
from order.models import OrderStatus

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('create_orders', type=int)
        parser.add_argument('number', type=int)

    def handle(self, *args, **options):
        create_orders = options['create_orders']

        if create_orders:
            self.create_orders(create_orders)

        self.run_performance_test(options['number'])

    def create_orders(self, count):
        current = Order.objects.count()
        print(f'Having {current} orders')
        print(f'Creating {count * 3} orders')
        for i in range(count):
            Order.objects.create()
            order2 = Order.objects.create()
            order3 = Order.objects.create()
            order2.cancel()
            order3.complete()

    def run_performance_test(self, number):
        import timeit
        print(timeit.timeit('from order.models import Order; Order.objects.get_cancelled_orders()', number=number))
        print(timeit.timeit('from order.models import Order; Order.objects.get_new_cancelled_orders()', number=number))
