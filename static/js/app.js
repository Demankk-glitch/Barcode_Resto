/**
 * OFF-PLATE BISTRO // E-MENU & CART STATE MANAGEMENT
 */

// State keranjang belanja di browser
const cartState = {};

// Format angka ke format mata uang Rupiah
function formatIDR(amount) {
    return 'IDR ' + Number(amount).toLocaleString('id-ID');
}

// Buka / Tutup Modal Keranjang Belanja
function toggleCartModal(isOpen) {
    const modal = document.getElementById('cart-modal');
    if (!modal) return;

    if (isOpen) {
        modal.classList.remove('opacity-0', 'pointer-events-none');
        modal.classList.add('opacity-100', 'pointer-events-auto');
        document.body.classList.add('overflow-hidden');
        renderCartItems();
    } else {
        modal.classList.add('opacity-0', 'pointer-events-none');
        modal.classList.remove('opacity-100', 'pointer-events-auto');
        document.body.classList.remove('overflow-hidden');
    }
}

// Event listener tombol trigger keranjang di navbar
document.addEventListener('DOMContentLoaded', () => {
    const openBtn = document.getElementById('cart-open-btn');
    if (openBtn) {
        openBtn.addEventListener('click', () => toggleCartModal(true));
    }

    // Periksa status sukses order dari URL parameter
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('order_success')) {
        // Hapus query param setelah notifikasi flash terlihat
        window.history.replaceState({}, document.title, window.location.pathname + (urlParams.get('meja') ? '?meja=' + urlParams.get('meja') : ''));
    }
});

// Stepper input: Tambah kuantitas di kartu menu
function incrementQty(id) {
    const input = document.getElementById(`qty-input-${id}`);
    if (input) {
        let val = parseInt(input.value) || 0;
        if (val < 50) {
            input.value = val + 1;
        }
    }
}

// Stepper input: Kurangi kuantitas di kartu menu
function decrementQty(id) {
    const input = document.getElementById(`qty-input-${id}`);
    if (input) {
        let val = parseInt(input.value) || 0;
        if (val > 0) {
            input.value = val - 1;
        }
    }
}

// Handler perubahan manual kuantitas
function onManualQtyChange(id) {
    const input = document.getElementById(`qty-input-${id}`);
    if (input) {
        let val = parseInt(input.value) || 0;
        if (val < 0) input.value = 0;
        if (val > 50) input.value = 50;
    }
}

// Tambah item ke Keranjang (Bag)
function addToBag(id) {
    const card = document.querySelector(`.menu-card[data-id="${id}"]`);
    const input = document.getElementById(`qty-input-${id}`);
    if (!card || !input) return;

    let qty = parseInt(input.value) || 0;
    // Jika kuantitas di input masih 0, defaultkan ke 1
    if (qty <= 0) {
        qty = 1;
        input.value = 1;
    }

    const name = card.dataset.name;
    const price = parseInt(card.dataset.price);

    cartState[id] = {
        id: id,
        name: name,
        price: price,
        qty: qty
    };

    updateCartBadges();
    
    // Efek visual tombol konfirmasi
    const btn = document.getElementById(`btn-add-${id}`);
    if (btn) {
        const originalText = btn.innerHTML;
        btn.innerHTML = '✓ TERSIMPAN DI BAG';
        btn.classList.add('bg-neon-lime', 'border-neon-lime');
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.classList.remove('bg-neon-lime', 'border-neon-lime');
        }, 1200);
    }
}

// Update kuantitas langsung dari dalam Modal Keranjang
function updateCartItemQty(id, delta) {
    if (!cartState[id]) return;

    cartState[id].qty += delta;
    if (cartState[id].qty <= 0) {
        delete cartState[id];
        // Sinkronkan input di halaman utama
        const input = document.getElementById(`qty-input-${id}`);
        if (input) input.value = 0;
    } else if (cartState[id].qty > 50) {
        cartState[id].qty = 50;
    } else {
        const input = document.getElementById(`qty-input-${id}`);
        if (input) input.value = cartState[id].qty;
    }

    renderCartItems();
    updateCartBadges();
}

// Hapus item dari keranjang
function removeCartItem(id) {
    if (cartState[id]) {
        delete cartState[id];
        const input = document.getElementById(`qty-input-${id}`);
        if (input) input.value = 0;
        renderCartItems();
        updateCartBadges();
    }
}

// Hitung total item dan total harga
function calculateCartTotals() {
    let totalCount = 0;
    let totalPrice = 0;

    for (const id in cartState) {
        totalCount += cartState[id].qty;
        totalPrice += cartState[id].qty * cartState[id].price;
    }

    return { totalCount, totalPrice };
}

// Perbarui badge counter di navbar & floating mobile bar
function updateCartBadges() {
    const { totalCount, totalPrice } = calculateCartTotals();

    const navCount = document.getElementById('nav-cart-count');
    if (navCount) navCount.innerText = totalCount;

    const mobileBar = document.getElementById('mobile-cart-bar');
    const mobileCount = document.getElementById('mobile-cart-count');
    const mobileTotal = document.getElementById('mobile-cart-total');

    if (mobileBar && mobileCount && mobileTotal) {
        mobileCount.innerText = totalCount;
        mobileTotal.innerText = formatIDR(totalPrice);

        if (totalCount > 0) {
            mobileBar.classList.remove('opacity-0', 'pointer-events-none');
            mobileBar.classList.add('opacity-100', 'pointer-events-auto');
        } else {
            mobileBar.classList.add('opacity-0', 'pointer-events-none');
            mobileBar.classList.remove('opacity-100', 'pointer-events-auto');
        }
    }
}

// Render daftar item di modal keranjang
function renderCartItems() {
    const container = document.getElementById('cart-items-container');
    const totalDisplay = document.getElementById('cart-total-price');
    const submitBtn = document.getElementById('btn-submit-order');
    const hiddenInputs = document.getElementById('hidden-inputs-wrapper');
    if (!container || !totalDisplay || !submitBtn || !hiddenInputs) return;

    const { totalCount, totalPrice } = calculateCartTotals();
    hiddenInputs.innerHTML = '';

    if (totalCount === 0) {
        container.innerHTML = `
            <div id="empty-cart-msg" class="py-16 text-center">
                <div class="font-mono text-4xl mb-3 text-zinc-700">[ 0 / 0 ]</div>
                <div class="font-grotesk font-black text-lg text-zinc-400 uppercase">KERANJANG MASIH KOSONG</div>
                <p class="font-mono text-xs text-zinc-500 mt-1 max-w-xs mx-auto">
                    Silakan pilih menu dari daftar di halaman untuk mulai membuat pesanan.
                </p>
            </div>
        `;
        totalDisplay.innerText = formatIDR(0);
        submitBtn.disabled = true;
        return;
    }

    let itemsHtml = '';
    for (const id in cartState) {
        const item = cartState[id];
        const itemSubtotal = item.qty * item.price;

        // Siapkan input hidden untuk pengiriman form
        hiddenInputs.innerHTML += `<input type="hidden" name="qty_${item.id}" value="${item.qty}">`;

        itemsHtml += `
            <div class="border-2 border-carbon-border bg-carbon-card p-3.5 flex items-center justify-between gap-3 shadow-sm">
                <div class="flex-1 min-w-0">
                    <h4 class="font-black text-sm text-white uppercase tracking-tight truncate">${item.name}</h4>
                    <span class="font-mono text-xs text-zinc-400">${formatIDR(item.price)} / porsi</span>
                </div>

                <div class="flex items-center gap-3">
                    <div class="flex items-center border border-zinc-700 bg-carbon">
                        <button type="button" onclick="updateCartItemQty(${item.id}, -1)" 
                                class="w-7 h-7 flex items-center justify-center font-mono font-bold text-zinc-300 hover:bg-zinc-800">-</button>
                        <span class="w-8 h-7 flex items-center justify-center font-mono text-xs font-bold text-white border-x border-zinc-700">${item.qty}</span>
                        <button type="button" onclick="updateCartItemQty(${item.id}, 1)" 
                                class="w-7 h-7 flex items-center justify-center font-mono font-bold text-zinc-300 hover:bg-zinc-800">+</button>
                    </div>

                    <div class="text-right min-w-[75px]">
                        <span class="font-grotesk font-bold text-sm text-neon-lime block">${formatIDR(itemSubtotal)}</span>
                        <button type="button" onclick="removeCartItem(${item.id})" class="font-mono text-[10px] text-zinc-500 hover:text-neon-red uppercase underline">HAPUS</button>
                    </div>
                </div>
            </div>
        `;
    }

    container.innerHTML = itemsHtml;
    totalDisplay.innerText = formatIDR(totalPrice);
    submitBtn.disabled = false;
}

// Filter kategori menu
function filterCategory(category) {
    const buttons = document.querySelectorAll('.category-btn');
    buttons.forEach(btn => {
        if (btn.innerText.includes(category) || (category === 'ALL' && btn.innerText.includes('SEMUA'))) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    const cards = document.querySelectorAll('.menu-card');
    cards.forEach(card => {
        if (category === 'ALL' || card.dataset.category === category) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });
}
