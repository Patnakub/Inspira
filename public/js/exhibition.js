const urlParams = new URLSearchParams(window.location.search);
const id = urlParams.get("id");
const exhibitionId = id;
const token = localStorage.getItem('token'); 
let exhibitionStatus = "";


if (!id) {
  alert("ไม่พบข้อมูลนิทรรศการ");
} else {
  function formatThaiDate(isoDate) {
    if (!isoDate || isNaN(new Date(isoDate).getTime())) return "-";
  
    const months = [
      'มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน',
      'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'
    ];
  
    const date = new Date(isoDate);
    const day = date.getDate();
    const month = months[date.getMonth()];
    const year = date.getFullYear();
  
    return `${day} ${month} ${year}`;
  }
  
  
  fetch(`http://localhost:5000/exhibitions/${id}`)
    .then(res => res.json())
    .then(ex => {
      exhibitionStatus = ex.status;
      document.getElementById("title").textContent = ex.title;
      document.getElementById("category").textContent = ex.categories?.join(", ") || "-";
      document.getElementById("cover").src = ex.cover_picture || ex.image || "";
      document.getElementById("location").textContent = ex.location || "-";

      function isValidDate(date) {
        return !isNaN(new Date(date).getTime());
      }
      
      if (typeof ex.start_date === 'string' && typeof ex.end_date === 'string') {
        document.getElementById("date").textContent = `${ex.start_date} – ${ex.end_date}`;
      } else {
        document.getElementById("date").textContent = "- - -";
      }
      
      

      if (ex.event_slot_time) {
        document.getElementById("time").textContent = ex.event_slot_time;
        document.getElementById("time-container").classList.remove("hidden");
      }

      const descContainer = document.getElementById("description");
      if (ex.description) {
        function linkify(text) {
          if (!text) return "";
          const urlPattern = /((https?:\/\/)[^\s<>()"]+)/g;
          return text.replace(urlPattern, (url) => {
            const cleanUrl = url.replace(/[)\]>]+$/, '');  // ตัด ) หรือ > หรือ ] ปิดท้าย
            return `<a href="${cleanUrl}" class="text-blue-600 underline break-words" target="_blank" rel="noopener noreferrer">${cleanUrl}</a>`;
          });
        }
      
        descContainer.innerHTML = linkify(ex.description);        
        descContainer.style.display = "block";
      }

      document.getElementById("ticket").textContent = ex.ticket || "-";

      if (Array.isArray(ex.ticket_price) && ex.ticket_price.length > 0) {
        const priceList = ex.ticket_price.join(", ");
        document.getElementById("ticket_price").textContent = `${priceList} บาท`;
        document.getElementById("price-container").classList.remove("hidden");
      } else if (typeof ex.ticket_price === "number" || typeof ex.ticket_price === "string") {
        document.getElementById("ticket_price").textContent = `${ex.ticket_price} บาท`;
        document.getElementById("price-container").classList.remove("hidden");
      }

      if (ex.url) {
        // ลบ HTML tag ปลายทาง เช่น </p> ) หรืออื่น ๆ
        let cleanUrl = ex.url.replace(/<\/?[^>]+(>|$)/g, "").replace(/[)\s]+$/, "").trim();
      
        // ตรวจสอบว่าเป็น http หรือ https เท่านั้น
        if (/^https?:\/\//.test(cleanUrl)) {
          document.getElementById("externalLink").href = cleanUrl;
          document.getElementById("externalLink").textContent = cleanUrl;
          document.getElementById("url-container").classList.remove("hidden");
        }
      }
      

        // ----- ปุ่ม Review -----
      const reviewBtn = document.querySelector('button.bg-green-600');
      reviewBtn?.addEventListener('click', () => {
        if (!token) {
          alert('กรุณาเข้าสู่ระบบก่อน');
        } else if (exhibitionStatus === "upcoming") {
          alert("ยังไม่สามารถรีวิวได้ในขณะนี้ กรุณารอให้นิทรรศการเริ่มจัดก่อน");
        } else {
          window.location.href = `review.html?id=${exhibitionId}`;
        }
  });  
  
    })
    .catch(err => {
      console.error("โหลดข้อมูลผิดพลาด:", err);
      alert("เกิดข้อผิดพลาดในการโหลดข้อมูลนิทรรศการ");
    });
}

window.addEventListener('DOMContentLoaded', () => {
  const userId = token ? JSON.parse(atob(token.split('.')[1])).id : null;

  // ----- Favorite -----
  const favBtn = document.querySelector('button.bg-yellow-400');
  let isFav = false;

  function updateFavButton() {
    favBtn.textContent = isFav ? '❤️ Favorited' : '🤍 Favorite';
  }

  async function checkFavStatus() {
    try {
      const res = await fetch(`http://localhost:5000/favorites/check/${exhibitionId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      isFav = data.favorited;
      updateFavButton();
    } catch (err) {
      console.error('Error checking favorite:', err);
    }
  }

  favBtn?.addEventListener('click', async () => {
    if (!token) {
      alert('กรุณาเข้าสู่ระบบก่อน');
      return;
    }

    try {
      if (isFav) {
        await fetch(`http://localhost:5000/favorites/${exhibitionId}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        isFav = false;
      } else {
        await fetch('http://localhost:5000/favorites', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ exhibition_id: exhibitionId })
        });
        isFav = true;
      }
      updateFavButton();
    } catch (err) {
      console.error('Error updating favorite:', err);
    }
  });

  checkFavStatus();

  // ----- ปุ่มแผนที่ -----
const mapBtn = document.getElementById("mapBtn");
mapBtn?.addEventListener('click', () => {
  window.location.href = `bus.html?id=${exhibitionId}`;
});


  // ----- ปุ่มบัญชี -----
  const accountBtn = document.getElementById('accountBtn');
  accountBtn?.addEventListener('click', () => {
    if (token) {
      window.location.href = 'account.html';
    } else {
      alert('กรุณาเข้าสู่ระบบก่อน');
    }
  });


  // ----- โหลดรีวิว -----
  let allReviews = [];
  let currentIndex = 0;
  const chunkSize = 3;

  async function fetchReviews() {
    try {
      const res = await fetch(`http://localhost:5000/reviews/${exhibitionId}`);
      const data = await res.json();
      if (!Array.isArray(data)) throw new Error("ข้อมูลรีวิวผิดพลาด");
      allReviews = data;
      renderInitialReviews();
    } catch (err) {
      console.error("โหลดรีวิวผิดพลาด:", err);
    }
  }

  function renderInitialReviews() {
    const userReviewContainer = document.getElementById("userReview");
    const otherReviewContainer = document.getElementById("otherReviews");
    const moreBtn = document.getElementById("loadMoreBtn");
    const reviewBtn = document.querySelector("button.bg-green-600");
  
    userReviewContainer.innerHTML = "";
    otherReviewContainer.innerHTML = "";
  
    // ✅ ถ้าไม่มีรีวิวเลย
    if (allReviews.length === 0) {
      otherReviewContainer.innerHTML = `<p class="text-gray-500 italic">ยังไม่มีรีวิว</p>`;
      return;
    }
  
    const userReview = allReviews.find(r => {
      const id = r.user_id._id || r.user_id;
      return id === userId;
    });
  
    const others = allReviews.filter(r => {
      const id = r.user_id._id || r.user_id;
      return id !== userId;
    });
  
    if (userReview) {
      userReviewContainer.innerHTML = renderReviewCard(userReview, true);
      if (reviewBtn) reviewBtn.classList.add("hidden");
    }
  
    const top2 = others.slice(0, 2);
    top2.forEach(r => {
      otherReviewContainer.insertAdjacentHTML("beforeend", renderReviewCard(r));
    });
  
    const totalReviews = allReviews.length;

    if (totalReviews > 2) {
      moreBtn.classList.remove("hidden");
      moreBtn.href = `all_reviews.html?id=${exhibitionId}`;
    }

  }
  
  
  function renderReviewCard(review, isUser = false) {
    const stars = '★'.repeat(review.rating) + '☆'.repeat(5 - review.rating);
    const username = isUser ? "รีวิวของคุณ" : (review.user_id?.username || "ผู้ใช้งาน");
    const editBtn = isUser
    ? `<button onclick="window.location.href='review.html?id=${exhibitionId}'" class="text-sm text-blue-600 hover:underline ml-2">แก้ไข</button>`
    : "";

  
    return `
      <div class="bg-gray-100 p-4 rounded shadow">
        <div class="flex items-center justify-between">
          <strong>${username}</strong>
          <div>
            <span class="text-yellow-500">${stars}</span>
            ${editBtn}
          </div>
        </div>
        <p class="text-sm mt-2">${review.review}</p>
        ${review.image_url ? `<img src="http://localhost:5000${review.image_url}" class="mt-2 rounded max-h-48" alt="รูปรีวิว">` : ""}
      </div>
    `;
  }
  
  fetchReviews();
  
});
