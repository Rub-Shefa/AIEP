from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models.deletion import ProtectedError
from django.shortcuts import render, redirect, get_object_or_404

from .forms import ProductForm
from .models import Product


def _get_seller_profile(request):
    return getattr(request.user, 'seller_profile', None)


@login_required
def seller_product_add(request):
    seller_profile = _get_seller_profile(request)
    if seller_profile is None:
        messages.error(request, "Only registered sellers can list products.")
        return redirect('seller_dashboard')

    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = seller_profile
            product.save()
            messages.success(request, f'"{product.name}" was added to your catalog.')
            return redirect('seller_dashboard')
    else:
        form = ProductForm()

    return render(request, 'catalog/product_form.html', {
        'form': form,
        'mode': 'add',
        'seller_profile': seller_profile,
    })


@login_required
def seller_product_edit(request, product_id):
    seller_profile = _get_seller_profile(request)
    if seller_profile is None:
        messages.error(request, "Only registered sellers can manage products.")
        return redirect('seller_dashboard')

    product = get_object_or_404(Product, id=product_id, seller=seller_profile)

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{product.name}" was updated.')
            return redirect('seller_dashboard')
    else:
        form = ProductForm(instance=product)

    return render(request, 'catalog/product_form.html', {
        'form': form,
        'mode': 'edit',
        'product': product,
        'seller_profile': seller_profile,
    })


@login_required
def seller_product_delete(request, product_id):
    seller_profile = _get_seller_profile(request)
    if seller_profile is None:
        messages.error(request, "Only registered sellers can manage products.")
        return redirect('seller_dashboard')

    product = get_object_or_404(Product, id=product_id, seller=seller_profile)

    if request.method == 'POST':
        name = product.name
        try:
            product.delete()
            messages.info(request, f'"{name}" was removed from your catalog.')
        except ProtectedError:
            messages.error(
                request,
                f'"{name}" can\'t be deleted because it already has orders attached to it. '
                'Set its stock to 0 to hide it from customers instead.'
            )
    return redirect('seller_dashboard')
