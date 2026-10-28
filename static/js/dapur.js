/**
 * OFF-PLATE BISTRO // KITCHEN DISPLAY SYSTEM (KDS)
 * Real-Time Dynamic Polling & Order Status Transitions
 */

let activeOrderIds = new Set();
let pollingInterval = null;

// Inisialisasi saat halaman KDS dimuat
document.addEventListener('DOMContentLoaded', () => {
    // Kumpulkan ID order yang sudah ter-render awal dari template SSR
    document.querySelectorAll('.order-card').forEach(card => {
        const id = parseInt(card.dataset.id);
        if (id) activeOrderIds.add(id);
    });

    updateSyncClock();

    // Mulai polling asinkron setiap 3000ms (3 detik)
    startLivePolling();
});

// Mulai timer polling berkala
function startLivePolling() {
    if (pollingInterval) clearInterval(pollingInterval);
    pollingInterval = setInterval(fetchActiveOrders, 3000);
}

// Fungsi polling dinamis ke endpoint backend Flask
async function fetchActiveOrders() {
    try {
        const response = await fetch('/api/dapur/pesanan', {
            headers: {
                'Accept': 'application/json'
            }
        });

        if (response.status === 401) {
            console.warn('Sesi staf berakhir. Menghentikan polling.');
            clearInterval(pollingInterval);
            window.location.href = '/dapur/login';
            return;
        }

        if (!response.ok) {
            console.error('Gagal mengambil data pesanan dapur:', response.status);
            return;
        }

        const data = await response.json();
        updateKdsInterface(data.pesanan || []);
        updateSyncClock(data.timestamp);

    } catch (error) {
        console.error('Kesalahan koneksi saat polling dapur:', error);
    }
}

// Perbarui jam sinkronisasi terakhir di header KDS
function updateSyncClock(serverTime) {
    const clock = document.getElementById('sync-clock');
    if (!clock) return;

    if (serverTime) {
        clock.innerText = serverTime + ' UTC';
    } else {
        const now = new Date();
        clock.innerText = now.toTimeString().split(' ')[0];
    }
}

// Perbarui DOM antrean pesanan secara dinamis tanpa refresh halaman
function updateKdsInterface(orders) {
    const ordersGrid = document.getElementById('orders-grid');
    const statCount = document.getElementById('stat-antrean-count');
    const activeTabCount = document.getElementById('active-tab-count');
    if (!ordersGrid) return;

    // Perbarui counter
    if (statCount) statCount.innerText = orders.length;
    if (activeTabCount) activeTabCount.innerText = orders.length;

    const incomingIds = new Set(orders.map(o => o.id));

    // 1. Hapus kartu pesanan yang sudah tidak aktif (misal sudah diselesaikan di tab/perangkat lain)
    activeOrderIds.forEach(id => {
        if (!incomingIds.has(id)) {
            const el = document.getElementById(`order-card-${id}`);
            if (el) el.remove();
            activeOrderIds.delete(id);
        }
    });

    // 2. Jika antrean kosong, tampilkan banner kosong
    if (orders.length === 0) {
        ordersGrid.innerHTML = `
            <div id="no-orders-banner" class="col-span-full py-16 text-center border-2 border-dashed border-zinc-800 bg-carbon-card">
                <div class="font-mono text-4xl text-zinc-700 mb-2">[ ANTRIAN BERSIH ]</div>
                <div class="font-grotesk text-xl font-black text-zinc-300 uppercase">BELUM ADA PESANAN MASUK</div>
                <p class="font-mono text-xs text-zinc-500 mt-1">
                    Layar akan berkedip dan menampilkan kartu tiket saat pelanggan mengirim pesanan baru.
                </p>
            </div>
        `;
        return;
    } else {
        const banner = document.getElementById('no-orders-banner');
        if (banner) banner.remove();
    }

    // 3. Tambahkan kartu pesanan baru yang belum ada di layar
    orders.forEach(order => {
        if (!activeOrderIds.has(order.id)) {
            activeOrderIds.add(order.id);
            const cardHtml = createOrderCardHtml(order, true);
            ordersGrid.insertAdjacentHTML('afterbegin', cardHtml);

            // Berikan efek audio feedback (beep sintetis Web Audio API jika didukung)
            playNewOrderBeep();
        }
    });
}

// Menghasilkan markup HTML kartu tiket pesanan dapur
function createOrderCardHtml(order, isNew = false) {
    let itemsList = '';
    order.items.forEach(item => {
        itemsList += `
            <li class="flex items-start justify-between border-b border-zinc-800/70 pb-2">
                <span class="font-bold text-white">
                    <span class="text-neon-amber font-mono font-black mr-1.5">[${item.kuantitas}x]</span> 
                    ${item.nama_menu}
                </span>
            </li>
        `;
    });

    let catatanHtml = '';
    if (order.catatan) {
        catatanHtml = `
            <div class="mt-4 p-2.5 border border-dashed border-zinc-700 bg-zinc-900/80 text-xs text-zinc-300">
                <span class="text-zinc-500 font-bold block uppercase text-[10px]">CATATAN MEJA:</span>
                "${order.catatan}"
            </div>
        `;
    }

    const flashClass = isNew ? 'new-order-flash' : '';

    return `
        <div class="order-card border-2 border-neon-amber bg-carbon-card flex flex-col justify-between shadow-brutalist-card transition-all duration-300 ${flashClass}"
             id="order-card-${order.id}" data-id="${order.id}">
            <div>
                <div class="p-4 border-b-2 border-zinc-800 flex items-center justify-between bg-zinc-900/60">
                    <div class="flex items-center gap-2">
                        <span class="w-3 h-3 bg-neon-amber rounded-full animate-ping"></span>
                        <span class="font-grotesk font-black text-xl text-white tracking-tight">
                            TABLE // ${order.nomor_meja}
                        </span>
                    </div>
                    <span class="font-mono text-xs bg-zinc-800 text-zinc-300 px-2 py-0.5 border border-zinc-700">
                        #${order.id} • ${order.created_at}
                    </span>
                </div>

                <div class="p-5 space-y-3 font-mono">
                    <div class="text-[11px] text-zinc-500 uppercase tracking-widest">[ITEM LIST]:</div>
                    <ul class="space-y-2 text-sm text-zinc-200">
                        ${itemsList}
                    </ul>
                    ${catatanHtml}
                </div>
            </div>

            <div class="p-4 border-t-2 border-zinc-800 bg-zinc-900/40 flex items-center justify-between gap-3">
                <span class="font-mono text-xs font-bold text-neon-amber bg-zinc-900 px-2.5 py-1 border border-neon-amber/50 uppercase">
                    STATUS: MENUNGGU
                </span>
                <button type="button" onclick="updateOrderStatus(${order.id}, 'Selesai')"
                        class="bg-white text-black font-black font-grotesk text-xs uppercase px-4 py-2 border-2 border-white hover:bg-neon-lime hover:border-neon-lime active:translate-x-0.5 active:translate-y-0.5 shadow-sm transition-all">
                    TANDAI SELESAI ✓
                </button>
            </div>
        </div>
    `;
}

// Ubah Status Pesanan dari 'Masuk' ke 'Selesai' via API asinkron
async function updateOrderStatus(orderId, newStatus) {
    const card = document.getElementById(`order-card-${orderId}`);
    const actionBtn = card ? card.querySelector('button') : null;

    if (actionBtn) {
        actionBtn.innerText = 'MEMPROSES...';
        actionBtn.disabled = true;
    }

    try {
        const response = await fetch(`/api/dapur/pesanan/${orderId}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ status: newStatus })
        });

        if (!response.ok) {
            const errData = await response.json();
            alert('Gagal memperbarui status: ' + (errData.error || response.statusText));
            if (actionBtn) {
                actionBtn.innerText = 'TANDAI SELESAI ✓';
                actionBtn.disabled = false;
            }
            return;
        }

        // Animasi keluar saat status berhasil diubah
        if (card) {
            card.style.transition = 'all 0.3s ease-out';
            card.style.transform = 'scale(0.95)';
            card.style.opacity = '0';
            setTimeout(() => {
                card.remove();
                activeOrderIds.delete(orderId);

                // Perbarui counter stat
                const count = activeOrderIds.size;
                const statCount = document.getElementById('stat-antrean-count');
                const activeTabCount = document.getElementById('active-tab-count');
                if (statCount) statCount.innerText = count;
                if (activeTabCount) activeTabCount.innerText = count;

                if (count === 0) {
                    const grid = document.getElementById('orders-grid');
                    if (grid) {
                        grid.innerHTML = `
                            <div id="no-orders-banner" class="col-span-full py-16 text-center border-2 border-dashed border-zinc-800 bg-carbon-card">
                                <div class="font-mono text-4xl text-zinc-700 mb-2">[ ANTRIAN BERSIH ]</div>
                                <div class="font-grotesk text-xl font-black text-zinc-300 uppercase">BELUM ADA PESANAN MASUK</div>
                                <p class="font-mono text-xs text-zinc-500 mt-1">
                                    Layar akan berkedip dan menampilkan kartu tiket saat pelanggan mengirim pesanan baru.
                                </p>
                            </div>
                        `;
                    }
                }
            }, 300);
        }

    } catch (err) {
        console.error('Kesalahan koneksi saat update status:', err);
        alert('Terjadi kesalahan jaringan saat memperbarui status.');
        if (actionBtn) {
            actionBtn.innerText = 'TANDAI SELESAI ✓';
            actionBtn.disabled = false;
        }
    }
}

// Switch tampilan antara tab Pesanan Aktif dan Riwayat Selesai
function switchKdsTab(tab) {
    const activeSection = document.getElementById('active-orders-section');
    const historySection = document.getElementById('history-orders-section');
    const activeBtn = document.getElementById('tab-active-btn');
    const historyBtn = document.getElementById('tab-history-btn');

    if (tab === 'active') {
        activeSection.classList.remove('hidden');
        historySection.classList.add('hidden');
        activeBtn.className = 'px-4 py-2 border-2 border-neon-lime bg-neon-lime text-black font-bold uppercase tracking-wider shadow-sm transition-all';
        historyBtn.className = 'px-4 py-2 border-2 border-zinc-800 bg-carbon-card text-zinc-400 font-bold uppercase tracking-wider hover:border-zinc-500 transition-all';
    } else {
        activeSection.classList.add('hidden');
        historySection.classList.remove('hidden');
        historyBtn.className = 'px-4 py-2 border-2 border-neon-lime bg-neon-lime text-black font-bold uppercase tracking-wider shadow-sm transition-all';
        activeBtn.className = 'px-4 py-2 border-2 border-zinc-800 bg-carbon-card text-zinc-400 font-bold uppercase tracking-wider hover:border-zinc-500 transition-all';
    }
}

// Notifikasi nada beep lembut saat pesanan baru masuk
function playNewOrderBeep() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, audioCtx.currentTime); // 880 Hz
        gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.3);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.3);
    } catch (e) {
        // Browser mungkin membatasi audio jika belum ada user gesture, abaikan dengan aman
    }
}
