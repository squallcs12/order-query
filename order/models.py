from django.db import models


class OrderQuerySet(models.QuerySet):
    def get_cancelled_orders(self):
        order_status = OrderStatus.objects.filter(order=models.OuterRef('pk'))
        latest_status = order_status.order_by('order', '-created_at').distinct('order').values('status')
        return self.annotate(sub=models.Subquery(latest_status)).filter(sub=OLD_STATUS_CANCELLED)

    def get_new_cancelled_orders(self):
        return self.filter(status=NEW_STATUS_CANCELLED)


OLD_STATUS_PENDING = 'Pending'
OLD_STATUS_COMPLETE = 'Complete'
OLD_STATUS_CANCELLED = 'Cancelled'

OLD_STATUS_CHOICES = (
    ('Pending', 'Pending'),
    ('Complete', 'Complete'),
    ('Cancelled', 'Cancelled'),
)

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
    # optimize for latest status
    status = models.SmallIntegerField(choices=NEW_STATUS_CHOICES, default=NEW_STATUS_PENDING)

    def cancel(self):
        self.status = NEW_STATUS_CANCELLED
        self.save()

        self.orderstatus_set.create(status=OLD_STATUS_CANCELLED)

    def complete(self):
        self.status = NEW_STATUS_COMPLETE
        self.save()

        self.orderstatus_set.create(status=OLD_STATUS_COMPLETE)

    class Meta:
        # optimize for query status faster
        indexes = [models.Index('status', name='index_by_status')]
        pass


class OrderStatus(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=OLD_STATUS_CHOICES, default=OLD_STATUS_PENDING)
    # optimize to integer field for status
    # status = models.SmallIntegerField(choices=NEW_STATUS_CHOICES, default=NEW_STATUS_PENDING)
