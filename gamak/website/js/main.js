/**
 * GAMAK.eu - Main JavaScript
 * Navigation, Cookie Banner, Animations, Form Handling
 */

document.addEventListener('DOMContentLoaded', function () {

    // ============================================
    // NAVBAR - scroll effect
    // ============================================
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }

    // ============================================
    // MOBILE MENU
    // ============================================
    const mobileToggle = document.getElementById('mobileToggle');
    const mobileMenu = document.getElementById('mobileMenu');
    const mobileCloseBtn = document.getElementById('mobileClose');

    if (mobileToggle && mobileMenu) {
        mobileToggle.addEventListener('click', function () {
            mobileMenu.classList.toggle('open');
            document.body.style.overflow = mobileMenu.classList.contains('open') ? 'hidden' : '';
        });

        if (mobileCloseBtn) {
            mobileCloseBtn.addEventListener('click', function () {
                mobileMenu.classList.remove('open');
                document.body.style.overflow = '';
            });
        }

        // Close mobile menu on link click
        mobileMenu.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', function () {
                mobileMenu.classList.remove('open');
                document.body.style.overflow = '';
            });
        });
    }

    // ============================================
    // MOBILE DROPDOWN TOGGLES
    // ============================================
    document.querySelectorAll('.mobile-dropdown-toggle').forEach(function (toggle) {
        toggle.addEventListener('click', function (e) {
            e.preventDefault();
            var items = this.nextElementSibling;
            if (items) {
                items.style.display = items.style.display === 'block' ? 'none' : 'block';
                this.classList.toggle('open');
            }
        });
    });

    // ============================================
    // COOKIE BANNER
    // ============================================
    var cookieBanner = document.getElementById('cookieBanner');
    var cookieAccept = document.getElementById('cookieAccept');
    var cookieSettings = document.getElementById('cookieSettings');

    if (cookieBanner) {
        // Check if cookies already accepted
        if (!localStorage.getItem('gamak_cookies_accepted')) {
            setTimeout(function () {
                cookieBanner.classList.add('visible');
            }, 1000);
        }

        if (cookieAccept) {
            cookieAccept.addEventListener('click', function () {
                localStorage.setItem('gamak_cookies_accepted', 'true');
                localStorage.setItem('gamak_cookies_date', new Date().toISOString());
                cookieBanner.classList.remove('visible');
            });
        }

        if (cookieSettings) {
            cookieSettings.addEventListener('click', function () {
                // Redirect to privacy policy
                window.location.href = 'polityka-prywatnosci.html#cookies';
            });
        }
    }

    // ============================================
    // AOS INIT (if loaded)
    // ============================================
    if (typeof AOS !== 'undefined') {
        AOS.init({
            duration: 700,
            once: true,
            offset: 80,
            easing: 'ease-out-cubic'
        });
    }

    // ============================================
    // CONTACT FORM HANDLING
    // ============================================
    var contactForm = document.getElementById('contactForm');
    if (contactForm) {
        contactForm.addEventListener('submit', function (e) {
            e.preventDefault();

            var formData = new FormData(contactForm);
            var data = {};
            formData.forEach(function (value, key) {
                data[key] = value;
            });

            // Basic validation
            if (!data.name || !data.email || !data.message) {
                showFormMessage('Proszę wypełnić wymagane pola.', 'error');
                return;
            }

            if (!isValidEmail(data.email)) {
                showFormMessage('Proszę podać poprawny adres email.', 'error');
                return;
            }

            // mailto fallback (no backend)
            var subject = encodeURIComponent(data.subject || 'Zapytanie ze strony gamak.eu');
            var body = encodeURIComponent(
                'Imię: ' + data.name + '\n' +
                'Email: ' + data.email + '\n' +
                'Telefon: ' + (data.phone || 'nie podano') + '\n' +
                'Temat: ' + (data.subject || 'brak') + '\n\n' +
                'Wiadomość:\n' + data.message
            );
            window.location.href = 'mailto:biuro@gamak.eu?subject=' + subject + '&body=' + body;

            showFormMessage('Dziękujemy! Otworzy się Twój klient pocztowy.', 'success');
        });
    }

    function isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    function showFormMessage(msg, type) {
        var existing = document.querySelector('.form-message');
        if (existing) existing.remove();

        var msgEl = document.createElement('div');
        msgEl.className = 'form-message';
        msgEl.style.cssText = 'padding:1rem;margin-top:1rem;font-size:0.9rem;font-weight:600;' +
            (type === 'error'
                ? 'background:rgba(255,50,50,0.1);border:1px solid rgba(255,50,50,0.3);color:#ff5050;'
                : 'background:rgba(8,172,242,0.1);border:1px solid rgba(8,172,242,0.3);color:#08ACF2;');
        msgEl.textContent = msg;
        contactForm.appendChild(msgEl);

        setTimeout(function () {
            if (msgEl.parentNode) msgEl.remove();
        }, 5000);
    }

    // ============================================
    // SMOOTH SCROLL for anchor links
    // ============================================
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            var targetId = this.getAttribute('href');
            if (targetId === '#') return;
            var target = document.querySelector(targetId);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // ============================================
    // ACTIVE NAV LINK HIGHLIGHT
    // ============================================
    var currentPage = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.navbar-menu a, .navbar-mobile a').forEach(function (link) {
        var href = link.getAttribute('href');
        if (href === currentPage) {
            link.classList.add('active');
        }
    });

});
