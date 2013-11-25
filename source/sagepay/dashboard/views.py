from django.views.generic import ListView, DetailView

from sagepay.models import SagePayTransaction

class TransactionListView(ListView):
    queryset = SagePayTransaction.objects.order_by('-created')
    context_object_name = 'transactions'
    template_name = 'sagepay/dashboard/transaction_list.html'


class TransactionDetailView(DetailView):
    model = SagePayTransaction
    context_object_name = 'txn'
    template_name = 'sagepay/dashboard/transaction_detail.html'
