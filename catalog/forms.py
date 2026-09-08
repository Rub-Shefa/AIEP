from django import forms
from .models import Product, Category

class ProductForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="Select a Category",
        widget=forms.Select(attrs={
            'class': 'w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-800 focus:border-teal focus:outline-none'
        })
    )

    class Meta:
        model = Product
        fields = ['name', 'category', 'price', 'stock', 'image', 'description', 'is_regulated']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-800 focus:border-teal focus:outline-none',
                'placeholder': 'Product name'
            }),
            'price': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0.01',
                'class': 'w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-800 focus:border-teal focus:outline-none',
                'placeholder': '0.00'
            }),
            'stock': forms.NumberInput(attrs={
                'min': '0',
                'class': 'w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-800 focus:border-teal focus:outline-none',
                'placeholder': '0'
            }),
            'image': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-slate-500 file:mr-4 file:rounded-xl file:border-0 file:bg-teal/10 file:px-4 file:py-2.5 file:text-xs file:font-bold file:text-teal hover:file:bg-teal hover:file:text-white transition cursor-pointer',
                'accept': 'image/*'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-800 focus:border-teal focus:outline-none',
                'placeholder': 'Product description, dosage, instructions...'
            }),
            'is_regulated': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 rounded border-slate-300 text-teal focus:ring-teal'
            }),
        }