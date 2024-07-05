# Order query
Take the following example schema:

- Model: Order
  - Field: ID
- Model: OrderStatus
  - Field: ID
  - Field: Created (DateTime)
  - Field: Status (Text: Pending/Complete/Cancelled)
  - Field: OrderID (ForeignKey)

We have a database of many Orders, and each Order has one or many OrderStatus records.
Each OrderStatus row has columns for created datetime and a status of Pending/Complete/Failed.
The status of every Order in the database is dictated by the most recent OrderStatus. 
A `Pending` OrderStatus will be created for an Order when it is first created, 
`Complete` OrderStatus is created after successful payment or `Cancelled` is created if payment fails, 
or also if a `Complete` Order is refunded it is also given status `Cancelled`. 

Using the Django ORM, how would you structure a query to list all `Cancelled` orders in the database
without changes to the schema. Given that the database may contain millions of Orders, 
what optimisations would you suggest to make through the use of other query techniques, 
technologies or schema changes to reduce burden on the database resources and improve response times.

Please use Django / Python for your solution. The logic and thought process demonstrated are the most 
important considerations rather than truly functional code, 
however code presentation is important as well as the technical aspect. 
If you cannot settle on a single perfect solution, 
you may also discuss alternative solutions to demonstrate your understanding of potential 
trade-offs as you encounter them. Of course if you consider a solution is too time-consuming you are also 
welcome to clarify or elaborate on potential improvements or multiple solution approaches 
conceptually to demonstrate understanding and planned solution.

## Solution
### Models
```python
OLD_STATUS_PENDING = 'Pending'
OLD_STATUS_CANCELLED = 'Cancelled'

OLD_STATUS_CHOICES = (
    ('Pending', 'Pending'),
    ('Complete', 'Complete'),
    ('Cancelled', 'Cancelled'),
)

class Order(models.Model):
    objects = OrderQuerySet.as_manager()


class OrderStatus(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.SmallIntegerField(choices=OLD_STATUS_CHOICES, default=OLD_STATUS_PENDING)
```

### Query
Let's define a test case cover the requirement
```python
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
```
To select the latest order status, we can use distinct on the order id and order by created_at desc.
```sql
SELECT DISTINCT ON (order_id) * FROM order_orderstatus ORDER BY order_id, created_at DESC;
```
Then to select orders with status `Cancelled`, we can use the following query.
```sql
SELECT * 
FROM
    order_order as o,
    (SELECT DISTINCT ON (order_id) * FROM order_status ORDER BY order_id, created_at DESC) as s
WHERE 
    o.id = s.order_id 
  AND s.status = 'Cancelled';
```
Translate this into django model query
```python
class OrderQuerySet(models.QuerySet):
    def get_cancelled_orders(self):
        order_status = OrderStatus.objects.filter(order=models.OuterRef('pk'))
        latest_status = order_status.order_by('order', '-created_at').distinct('order').values('status')
        return self.annotate(sub=models.Subquery(latest_status)).filter(sub=OLD_STATUS_CANCELLED)
```
Then we run the test to see this is working correctly.

### Optimisation 1
The above solution has BigO(n^2) because it join 2 tables and filter the result.
If there are many orders, this query will be slow.
So we can use a column to track the latest status in order to reduce the query time.
```python
class Order(models.Model):
    objects = OrderQuerySet.as_manager()
    # optimize for latest status
    status = models.SmallIntegerField(choices=OLD_STATUS_CHOICES, default=OLD_STATUS_PENDING)
```

When creating new order status, we need to update the order status as well.
```python
class Order(models.Model):
    def cancel(self):
        self.status = NEW_STATUS_CANCELLED
        self.save()

        self.orderstatus_set.create(status=OLD_STATUS_CANCELLED)

    def complete(self):
        self.status = NEW_STATUS_COMPLETE
        self.save()

        self.orderstatus_set.create(status=OLD_STATUS_COMPLETE)
```

Then we can update the query to use the cache column.
```python
class OrderQuerySet(models.QuerySet):
    def get_cancelled_orders(self):
        return self.filter(status=OLD_STATUS_CANCELLED)
```
This is a BigO(n) query because it only query the order table. Thus, it will be faster.

### Optimisation 2
Because the status have only 3 choices, we can change the status to integer to reduce the storage size.
```python
NEW_STATUS_PENDING = 0
NEW_STATUS_COMPLETE = 1
NEW_STATUS_CANCELLED = 2

NEW_STATUS_CHOICES = (
    (0, 'Pending'),
    (1, 'Complete'),
    (2, 'Cancelled'),
)


class Order(models.Model):
    objects = OrderQuerySet.as_manager()
    status = models.SmallIntegerField(choices=NEW_STATUS_CHOICES, default=NEW_STATUS_PENDING)


class OrderStatus(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.SmallIntegerField(choices=NEW_STATUS_CHOICES, default=NEW_STATUS_PENDING)
```

Then we can also add an index to the status column to speed up the query.
```python
class Order(models.Model):
    objects = OrderQuerySet.as_manager()
    status = models.SmallIntegerField(choices=NEW_STATUS_CHOICES, default=NEW_STATUS_PENDING)
    class Meta:
        indexes = [
            models.Index(fields=['status']),
        ]
```

With this, the query is faster because it only query the order table and the status column is indexed.
But this will increase the storage size and inserting/updating data will cost more time.
Use this only if the "select cancelled order" query is more frequent than the "insert/update order status" query.

We can run the 2nd test case to verify this is working correctly.
```python
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
```
## CI
https://github.com/squallcs12/order-query/actions
