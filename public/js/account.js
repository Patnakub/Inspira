document.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem('token');
    
    if (!token) {
      alert('กรุณาเข้าสู่ระบบก่อน');
      window.location.href = '/public/login.html';
      return;
    }
  
    // ดึงรายการ Favorite
    await loadFavorites(token);
    
    // ดึงรีวิวของผู้ใช้
    await loadReviewedExhibitions(token);
  });
  
  async function loadFavorites(token) {
    try {
      const res = await fetch('http://localhost:5000/favorites', {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
  
      const favorites = await res.json();
      const container = document.getElementById('favorite-container');
  
      if (!favorites.length) {
        container.innerHTML = `<p class="text-gray-600 text-center col-span-3">คุณยังไม่มีรายการที่ Favorite ไว้</p>`;
        return;
      }
  
      favorites.forEach(fav => {
        const ex = fav.exhibition_id;
        if (!ex || !ex._id) return; // ⛔ ข้ามถ้าไม่มีข้อมูลนิทรรศการ
      
        const card = document.createElement('a');
        card.href = `exhibition.html?id=${ex._id}`;
        card.className = 'block bg-white rounded-lg overflow-hidden shadow hover:shadow-xl transition';
      
        card.innerHTML = `
          <img src="${ex.cover_picture || '#'}" alt="${ex.title}" class="w-full h-56 object-cover">
          <div class="p-4">
            <h3 class="text-lg font-semibold mb-1">${ex.title}</h3>
            <p class="text-sm text-gray-600">${ex.location || '-'}</p>
            <p class="text-sm text-gray-500">${ex.start_date} – ${ex.end_date}</p>
          </div>
        `;
      
        container.appendChild(card);
      });
      
  
    } catch (err) {
      console.error('โหลดรายการ Favorite ผิดพลาด:', err);
      alert('เกิดข้อผิดพลาดในการโหลดรายการ Favorite');
    }
  }
  
  async function loadReviewedExhibitions(token) {
    try {
      const res = await fetch(`http://localhost:5000/reviews/me/all`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const reviews = await res.json();
      
      const container = document.getElementById("reviewedExhibitions");
      container.innerHTML = ""; // เคลียร์พื้นที่ก่อนแสดงข้อมูลใหม่
      
      if (reviews.length === 0) {
        container.innerHTML = "<p>ยังไม่มีรีวิว</p>"; // หากไม่มีรีวิวแสดงข้อความ
      }
      
      reviews.forEach(r => {
        const exhibition = r.exhibition_id;  // นิทรรศการที่ถูกรีวิว
        const stars = '★'.repeat(r.rating) + '☆'.repeat(5 - r.rating); // แสดงจำนวนดาว
      
        // ตรวจสอบว่า cover_picture เป็น URL แบบสมบูรณ์หรือไม่
        let imageUrl = exhibition.cover_picture;
        if (imageUrl && !imageUrl.startsWith('http')) {
          imageUrl = `https://api.thailandexhibition.com${imageUrl}`; // เพิ่ม URL พื้นฐาน
        }
      
        const image = imageUrl 
        ? `<img src="${imageUrl}" alt="${exhibition.title}" class="w-full h-32 object-cover border-2 border-gray-300 rounded-lg">` 
        : `<img src="path/to/default/image.jpg" alt="No Image" class="w-full h-32 object-cover border-2 border-gray-300 rounded-lg">`;

      
        // สร้างการ์ดนิทรรศการที่รีวิวแล้ว
        container.insertAdjacentHTML("beforeend", `
          <div class="bg-white p-4 rounded shadow">
            <a href="exhibition.html?id=${exhibition._id}" class="block">
              <div class="flex justify-between items-center">
                <strong>${exhibition.title}</strong>
                <div>
                  <span class="text-yellow-500">${stars}</span>
                </div>
              </div>
              ${image}  <!-- รูปภาพนิทรรศการจะถูกแสดงที่นี่ -->
              <div class="mt-2">
                <p><strong>สถานที่:</strong> ${exhibition.location || '-'}</p>
                <p><strong>วันที่:</strong> ${exhibition.start_date} - ${exhibition.end_date}</p>
              </div>
            </a>
          </div>
        `);
      });
      
    } catch (err) {
      console.error("โหลดรีวิวล้มเหลว:", err);
      alert("เกิดข้อผิดพลาดในการโหลดรีวิว");
    }
  }
  
  
  document.getElementById('logoutBtn')?.addEventListener('click', () => {
    localStorage.removeItem('token'); // ✅ ลบ token
    alert('คุณได้ออกจากระบบแล้ว');
    window.location.href = 'index.html';
  });
  