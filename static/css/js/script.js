const sections = document.querySelectorAll('.section');

function revealOnScroll() {
    sections.forEach((el) => {
        const pos = el.getBoundingClientRect().top;
        if (pos < window.innerHeight - 100) {
            el.classList.add('show');
        }
    });
}

window.addEventListener('scroll', revealOnScroll);
revealOnScroll();

const authCard = document.querySelector('.auth-card[data-active-form]');
if (authCard) {
    const tabs = authCard.querySelectorAll('.auth-tab');
    const forms = authCard.querySelectorAll('.auth-form');
    const openButtons = authCard.querySelectorAll('[data-open]');
    const emailRegex = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

    const setActiveForm = (target) => {
        tabs.forEach((tab) => {
            tab.classList.toggle('is-active', tab.dataset.target === target);
        });

        forms.forEach((form) => {
            form.classList.toggle('is-active', form.dataset.form === target);
            if (form.dataset.form !== target) {
                clearInlineAlert(form);
            }
        });
    };

    const messageElementFor = (input) => {
        if (!input.id) return null;
        return authCard.querySelector(`.field-message[data-for="${input.id}"]`);
    };

    const setFieldState = (input, isValid, message) => {
        const messageEl = messageElementFor(input);
        input.classList.remove('is-valid', 'is-invalid');
        if (!input.value.trim()) {
            if (messageEl) messageEl.textContent = '';
            return;
        }

        input.classList.add(isValid ? 'is-valid' : 'is-invalid');
        if (messageEl) {
            messageEl.textContent = message || '';
        }
    };

    const clearInlineAlert = (form) => {
        const alert = form.querySelector('.auth-inline-alert');
        if (!alert) return;
        alert.textContent = '';
        alert.classList.remove('is-visible');
    };

    const showInlineAlert = (form, message) => {
        const alert = form.querySelector('.auth-inline-alert');
        if (!alert) return;
        alert.textContent = message;
        alert.classList.add('is-visible');
    };

    const evaluatePasswordRules = (passwordValue) => {
        return {
            length: passwordValue.length >= 8,
            upper: /[A-Z]/.test(passwordValue),
            lower: /[a-z]/.test(passwordValue),
            digit: /\d/.test(passwordValue),
        };
    };

    const updatePasswordRulesUI = (form, sourceInputId, rulesResult) => {
        const list = form.querySelector(`[data-rules-for="${sourceInputId}"]`);
        if (!list) return;
        Object.entries(rulesResult).forEach(([key, isOk]) => {
            const item = list.querySelector(`[data-check="${key}"]`);
            if (item) {
                item.classList.toggle('is-ok', isOk);
            }
        });
    };

    const validateInput = (input) => {
        const value = input.value.trim();
        const rule = input.dataset.rule;
        const form = input.closest('.auth-form');

        if (!rule) {
            return true;
        }

        if (rule === 'required') {
            const ok = value.length > 0;
            setFieldState(input, ok, ok ? 'Correcto.' : 'Este campo es obligatorio.');
            return ok;
        }

        if (rule === 'email') {
            const ok = emailRegex.test(value);
            setFieldState(input, ok, ok ? 'Correo válido.' : 'Formato requerido: usuario@dominio.com');
            return ok;
        }

        if (rule === 'name') {
            const ok = value.length >= 3;
            setFieldState(input, ok, ok ? 'Nombre correcto.' : 'Ingresa nombre y apellido (mínimo 3 caracteres).');
            return ok;
        }

        if (rule === 'password') {
            const rulesResult = evaluatePasswordRules(value);
            const ok = Object.values(rulesResult).every(Boolean);
            if (form) {
                updatePasswordRulesUI(form, input.id, rulesResult);
            }
            setFieldState(
                input,
                ok,
                ok ? 'Contraseña segura.' : 'No cumple todos los requisitos de seguridad.'
            );
            return ok;
        }

        if (rule === 'code6') {
            const ok = /^\d{6}$/.test(value);
            setFieldState(input, ok, ok ? 'Código válido.' : 'Ingresa un código numérico de 6 dígitos.');
            return ok;
        }

        if (rule === 'confirm-password') {
            const sourceId = input.dataset.passwordSource;
            const source = sourceId ? authCard.querySelector(`#${sourceId}`) : null;
            const ok = Boolean(source) && value.length > 0 && source.value === input.value;
            setFieldState(input, ok, ok ? 'Las contraseñas coinciden.' : 'Debe coincidir con la contraseña.');
            return ok;
        }

        return true;
    };

    forms.forEach((form) => {
        const inputs = form.querySelectorAll('input[data-rule]');

        inputs.forEach((input) => {
            input.addEventListener('input', () => {
                validateInput(input);
                if (input.dataset.rule === 'password') {
                    const confirmTargets = form.querySelectorAll(`input[data-rule="confirm-password"][data-password-source="${input.id}"]`);
                    confirmTargets.forEach((confirmInput) => {
                        if (confirmInput.value) {
                            validateInput(confirmInput);
                        }
                    });
                }
            });

            input.addEventListener('blur', () => validateInput(input));
        });

        form.addEventListener('submit', (event) => {
            clearInlineAlert(form);
            let firstInvalid = null;
            let hasErrors = false;

            inputs.forEach((input) => {
                const valid = validateInput(input);
                if (!valid) {
                    hasErrors = true;
                    if (!firstInvalid) {
                        firstInvalid = input;
                    }
                }
            });

            if (hasErrors) {
                event.preventDefault();
                showInlineAlert(form, 'Revisa los campos marcados y corrige los requisitos antes de continuar.');
                if (firstInvalid) {
                    firstInvalid.focus();
                }
            }
        });
    });

    tabs.forEach((tab) => {
        tab.addEventListener('click', () => setActiveForm(tab.dataset.target));
    });

    openButtons.forEach((button) => {
        button.addEventListener('click', () => setActiveForm(button.dataset.open));
    });

    setActiveForm(authCard.dataset.activeForm || 'login');
}