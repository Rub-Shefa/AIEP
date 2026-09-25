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
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = seller
            product.save()

            if product.image:
                product.image_url = ''
                product.save(update_fields=['image_url'])

            messages.success(request, f"'{product.name}' was listed successfully!")
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
        messages.error(request, "Unauthorized access.")
        return redirect('seller_dashboard')

    product = get_object_or_404(Product, pk=pk, seller=seller)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            updated_product = form.save(commit=False)
            # If a new image was uploaded from the device, update image_url
            if 'image' in request.FILES and updated_product.image:
                updated_product.image_url = ''
            updated_product.save()

            messages.success(request, f"'{updated_product.name}' was updated successfully!")
            return redirect('seller_dashboard')
        else:
            messages.error(request, "Unable to save updates. Please check highlighted errors.")
    else:
        # Pre-fills form fields with current product values
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
        name = product.name
        product.delete()
        messages.success(request, f"'{name}' was removed from your catalog.")
    return redirect('seller_dashboard')
