from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Product, Category
from .forms import ProductForm

def _get_seller_profile(user):
    return getattr(user, 'seller_profile', None)

@login_required
def seller_product_add(request):
    seller = _get_seller_profile(request.user)
    if not seller:
        messages.error(request, "Only registered sellers can upload products.")
        return redirect('seller_dashboard')

    if request.method == 'POST':
        # request.FILES is mandatory for device file uploads!
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = seller
            if product.image:
                product.image_url = product.image.url
            product.save()
            messages.success(request, f"'{product.name}' was added successfully!")
            return redirect('seller_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProductForm()

    return render(request, 'catalog/product_form.html', {
        'form': form,
        'action': 'List Product'
    })

@login_required
def seller_product_edit(request, pk):
    seller = _get_seller_profile(request.user)
    if not seller:
        messages.error(request, "Unauthorized.")
        return redirect('seller_dashboard')

    product = get_object_or_404(Product, pk=pk, seller=seller)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            updated = form.save(commit=False)
            if updated.image:
                updated.image_url = updated.image.url
            updated.save()
            messages.success(request, f"'{product.name}' updated successfully.")
            return redirect('seller_dashboard')
        else:
            messages.error(request, "Error updating product.")
    else:
        form = ProductForm(instance=product)

    return render(request, 'catalog/product_form.html', {
        'form': form,
        'product': product,
        'action': 'Update Product'
    })

@login_required
def seller_product_delete(request, pk):
    if request.method == 'POST':
        seller = _get_seller_profile(request.user)
        product = get_object_or_404(Product, pk=pk, seller=seller)
        product.delete()
        messages.success(request, "Product deleted.")
    return redirect('seller_dashboard')