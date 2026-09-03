from django import forms
from .models import Product, Category

INPUT_STYLE = (
    'w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm bg-white '
    'focus:ring-2 focus:ring-teal/30 focus:border-teal outline-none transition-all'
)
TEXTAREA_STYLE = INPUT_STYLE + ' resize-none'
CHECKBOX_STYLE = 'h-4 w-4 rounded border-slate-300 text-teal focus:ring-teal'


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'description', 'price', 'stock',
            'dosage', 'certifications', 'is_regulated', 'image_url',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_STYLE, 'placeholder': 'e.g. Rapid Antigen Test Cassettes (Pack of 50)',
            }),
            'category': forms.Select(attrs={'class': INPUT_STYLE}),
            'description': forms.Textarea(attrs={
                'class': TEXTAREA_STYLE, 'rows': 3, 'placeholder': 'What is it, and who is it for?',
            }),
            'price': forms.NumberInput(attrs={'class': INPUT_STYLE, 'step': '0.01', 'min': '0'}),
            'stock': forms.NumberInput(attrs={'class': INPUT_STYLE, 'min': '0'}),
            'dosage': forms.TextInput(attrs={
                'class': INPUT_STYLE, 'placeholder': 'e.g. 500mg tablet, single-use',
            }),
            'certifications': forms.TextInput(attrs={
                'class': INPUT_STYLE, 'placeholder': 'e.g. FDA Approved, ISO-13485',
            }),
            'is_regulated': forms.CheckboxInput(attrs={'class': CHECKBOX_STYLE}),
            'image_url': forms.URLInput(attrs={
                'class': INPUT_STYLE, 'placeholder': 'https://images.example.com/product.jpg',
            }),
        }
        labels = {
            'is_regulated': 'This product is a regulated / prescription item',
            'image_url': 'Image URL',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.order_by('name')
        self.fields['category'].empty_label = 'Select a category'
        for name in ('description', 'dosage', 'certifications', 'image_url'):
            self.fields[name].required = False

    def clean_price(self):
        price = self.cleaned_data['price']
        if price is None or price <= 0:
            raise forms.ValidationError('Price must be greater than zero.')
        return price

    def clean_stock(self):
        stock = self.cleaned_data['stock']
        if stock is None or stock < 0:
            raise forms.ValidationError('Stock cannot be negative.')
        return stock
