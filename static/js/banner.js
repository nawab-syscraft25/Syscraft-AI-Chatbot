// banner.js

async function loadBanners() {
    const url = 'https://portal.lotuselectronics.com/web-api/home/home_slider?city=null';

    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'accept': 'application/json, text/plain, */*',
                'auth-key': 'Web2@!9',
                'enctype': 'multipart/form-data',
                'end-client': 'Lotus-Web',
                'origin': 'https://www.lotuselectronics.com',
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        const banners = result?.data?.banner ?? [];

        if (banners.length === 0) return;

        const carouselId = 'bannerCarousel';

        const carouselWrapper = document.createElement('div');
        carouselWrapper.className = 'carousel slide mt-2';
        carouselWrapper.id = carouselId;
        carouselWrapper.setAttribute('data-bs-ride', 'carousel');
        carouselWrapper.setAttribute('data-bs-interval', '3000');

        const inner = document.createElement('div');
        inner.className = 'carousel-inner  shadow';

        banners.forEach((banner, index) => {
            const item = document.createElement('div');
            item.className = 'carousel-item' + (index === 0 ? ' active' : '');

            const link = document.createElement('a');
            link.href = banner.banner_url;
            link.target = '_blank';

            const img = document.createElement('img');
            img.src = banner.banner_image;
            img.className = 'd-block w-100';
            img.alt = 'Banner';

            link.appendChild(img);
            item.appendChild(link);
            inner.appendChild(item);
        });

        // Optionally add indicators
        const indicators = document.createElement('div');
        indicators.className = 'carousel-indicators';
        banners.forEach((_, idx) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.setAttribute('data-bs-target', `#${carouselId}`);
            btn.setAttribute('data-bs-slide-to', idx);
            if (idx === 0) btn.className = 'active';
            indicators.appendChild(btn);
        });

        carouselWrapper.appendChild(indicators);
        carouselWrapper.appendChild(inner);

        // Optionally add controls
        const prevBtn = `
            <button class="carousel-control-prev" type="button" data-bs-target="#${carouselId}" data-bs-slide="prev">
                <span class="carousel-control-prev-icon"></span>
            </button>`;
        const nextBtn = `
            <button class="carousel-control-next" type="button" data-bs-target="#${carouselId}" data-bs-slide="next">
                <span class="carousel-control-next-icon"></span>
            </button>`;
        carouselWrapper.insertAdjacentHTML('beforeend', prevBtn + nextBtn);

        // Inject carousel below quick actions
        const quickActionsDiv = document.getElementById('quickActions');
        if (quickActionsDiv) {
            quickActionsDiv.insertAdjacentElement('afterend', carouselWrapper);
        }

    } catch (error) {
        console.error('Error loading banners:', error);
    }
}

document.addEventListener('DOMContentLoaded', loadBanners);
