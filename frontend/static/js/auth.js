/**
 * AgriCare — Authentication JavaScript
 * Local email/password sign-in, sign-up, forgot password, and reset password.
 *
 * Flow:
 *   • Sign In  → POST /login        → redirect to next or /detect
 *   • Sign Up  → POST /signup       → auto-login, redirect to next or /detect
 *   • Forgot   → POST /forgot-password → shows reset link (local/dev)
 *   • Reset    → POST /reset-password/<token> → redirect to /auth
 */

(function () {
    const cfg = window.AGRICARE || {};
    const errorBox = document.getElementById('authError');
    const successBox = document.getElementById('authSuccess');

    function showError(msg) {
        if (!errorBox) return;
        errorBox.hidden = false;
        errorBox.innerHTML = '<i class="bi bi-exclamation-circle-fill"></i> ' + msg;
        if (successBox) successBox.hidden = true;
    }

    function showSuccess(msg) {
        if (!successBox) return;
        successBox.hidden = false;
        successBox.innerHTML = '<i class="bi bi-check-circle-fill"></i> ' + msg;
        if (errorBox) errorBox.hidden = true;
    }

    function setLoading(btn, on) {
        if (!btn) return;
        btn.disabled = on;
        const text = btn.querySelector('.btn-text');
        if (text) text.textContent = on ? 'Please wait…' : btn.dataset.originalText || 'Submit';
    }

    // ─── Tab switching (Sign In / Sign Up) ───
    const tabBtns = document.querySelectorAll('.auth-tab-btn');
    const forms = document.querySelectorAll('.auth-form');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Update active tab
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Show the matching form
            const tab = btn.dataset.tab;
            forms.forEach(form => {
                form.style.display = form.id === tab + 'Form' ? 'flex' : 'none';
            });

            // Clear errors
            if (errorBox) errorBox.hidden = true;
        });
    });

    // ─── Show password toggle ───
    const toggleBtns = document.querySelectorAll('.btn-show-password');
    toggleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const wrapper = btn.closest('.password-wrapper');
            const input = wrapper.querySelector('input');
            if (input.type === 'password') {
                input.type = 'text';
                btn.classList.add('active');
                btn.innerHTML = '<i class="bi bi-eye"></i>';
            } else {
                input.type = 'password';
                btn.classList.remove('active');
                btn.innerHTML = '<i class="bi bi-eye-slash"></i>';
            }
        });
    });

    // ─── Sign In form ───
    const signinForm = document.getElementById('signinForm');
    if (signinForm) {
        signinForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (errorBox) errorBox.hidden = true;

            const submitBtn = signinForm.querySelector('button[type="submit"]');
            const formData = new FormData(signinForm);
            const payload = {
                email: formData.get('email'),
                password: formData.get('password'),
                next: cfg.NEXT || '/detect',
            };

            setLoading(submitBtn, true);
            try {
                const resp = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                const data = await resp.json();
                if (data.success) {
                    window.location.href = data.redirect || '/detect';
                } else {
                    showError(data.error || 'Sign in failed. Please try again.');
                }
            } catch (e) {
                showError('Network error. Please check your connection and try again.');
            } finally {
                setLoading(submitBtn, false);
            }
        });
    }

    // ─── Sign Up form ───
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (errorBox) errorBox.hidden = true;

            const submitBtn = signupForm.querySelector('button[type="submit"]');
            const formData = new FormData(signupForm);
            const password = formData.get('password');
            const confirmPassword = formData.get('confirm_password');

            // Client-side validation
            if (password !== confirmPassword) {
                showError('Passwords do not match.');
                return;
            }

            const payload = {
                full_name: formData.get('full_name'),
                email: formData.get('email'),
                password: password,
                next: cfg.NEXT || '/detect',
            };

            setLoading(submitBtn, true);
            try {
                const resp = await fetch('/signup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                const data = await resp.json();
                if (data.success) {
                    window.location.href = data.redirect || '/detect';
                } else {
                    showError(data.error || 'Sign up failed. Please try again.');
                }
            } catch (e) {
                showError('Network error. Please check your connection and try again.');
            } finally {
                setLoading(submitBtn, false);
            }
        });
    }

    // ─── Forgot Password form ───
    const forgotForm = document.getElementById('forgotForm');
    if (forgotForm) {
        forgotForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (errorBox) errorBox.hidden = true;

            const submitBtn = forgotForm.querySelector('button[type="submit"]');
            const formData = new FormData(forgotForm);
            const payload = {
                email: formData.get('email'),
            };

            setLoading(submitBtn, true);
            try {
                const resp = await fetch('/forgot-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                const data = await resp.json();
                if (data.success) {
                    if (data.reset_link) {
                        // Local/dev mode: show the reset link
                        showSuccess(data.message + ' <a href="' + data.reset_link + '" class="auth-forgot" style="display:inline-block;margin-top:8px;">Click here to reset your password</a>');
                    } else {
                        showSuccess(data.message);
                    }
                } else {
                    showError(data.error || 'Could not send reset link.');
                }
            } catch (e) {
                showError('Network error. Please check your connection and try again.');
            } finally {
                setLoading(submitBtn, false);
            }
        });
    }

    // ─── Reset Password form ───
    const resetForm = document.getElementById('resetForm');
    if (resetForm) {
        resetForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (errorBox) errorBox.hidden = true;

            const submitBtn = resetForm.querySelector('button[type="submit"]');
            const token = document.getElementById('resetToken').value;
            const formData = new FormData(resetForm);
            const password = formData.get('password');
            const confirmPassword = formData.get('confirm_password');

            // Client-side validation
            if (password !== confirmPassword) {
                showError('Passwords do not match.');
                return;
            }

            const payload = {
                password: password,
            };

            setLoading(submitBtn, true);
            try {
                const resp = await fetch('/reset-password/' + token, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                const data = await resp.json();
                if (data.success) {
                    showSuccess(data.message + ' <a href="/auth" class="auth-forgot" style="display:inline-block;margin-top:8px;">Click here to sign in</a>');
                } else {
                    showError(data.error || 'Could not reset password.');
                }
            } catch (e) {
                showError('Network error. Please check your connection and try again.');
            } finally {
                setLoading(submitBtn, false);
            }
        });
    }
})();
