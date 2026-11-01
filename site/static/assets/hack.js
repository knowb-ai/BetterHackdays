// BetterHackdays RFP Connector manual: progressive enhancement.
// Without this script the page is a complete, readable document; with it you
// get the typed console, scrollspy index, search palette, copy buttons, tabs,
// heading anchors, and expandable RFP rows.
(function () {
    var motion = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // --- Scroll progress ---
    var bar = document.getElementById('progress-bar');
    function progress() {
        var max = document.documentElement.scrollHeight - window.innerHeight;
        bar.style.width = (max > 0 ? (window.scrollY / max) * 100 : 0) + '%';
    }
    window.addEventListener('scroll', progress, { passive: true });
    progress();

    // --- Typed console ---
    var consoleEl = document.querySelector('.console');
    if (consoleEl && motion) {
        var lines = Array.prototype.slice.call(consoleEl.querySelectorAll('.console-log li'));
        consoleEl.classList.add('is-typing');
        var i = 0;
        (function next() {
            if (i > 0) lines[i - 1].classList.remove('is-active');
            if (i >= lines.length) return;
            var line = lines[i];
            line.classList.add('is-shown', 'is-active');
            i += 1;
            var delay = line.classList.contains('you') ? 1100 : line.classList.contains('call') ? 700 : 380;
            setTimeout(next, delay);
        })();
    }

    // --- Flight plan lights up when seen ---
    var plan = document.querySelector('.flightplan');
    if (plan && 'IntersectionObserver' in window) {
        new IntersectionObserver(function (entries, obs) {
            if (entries[0].isIntersecting) {
                plan.classList.add('is-lit');
                obs.disconnect();
            }
        }, { threshold: 0.4 }).observe(plan);
    } else if (plan) {
        plan.classList.add('is-lit');
    }

    // --- Heading anchors ---
    document.querySelectorAll('.doc h2[id], .doc h3[id]').forEach(function (h) {
        var a = document.createElement('a');
        a.className = 'heading-anchor';
        a.href = '#' + h.id;
        a.textContent = '#';
        a.setAttribute('aria-label', 'Link to ' + h.textContent);
        h.insertBefore(a, h.firstChild);
    });

    // --- Copy buttons ---
    document.querySelectorAll('.doc pre:not(.sig)').forEach(function (pre) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'copy';
        btn.textContent = 'Copy';
        btn.setAttribute('aria-label', 'Copy code');
        btn.addEventListener('click', function () {
            var text = pre.querySelector('code').innerText;
            var done = function () {
                btn.textContent = 'Copied';
                btn.classList.add('is-done');
                setTimeout(function () {
                    btn.textContent = 'Copy';
                    btn.classList.remove('is-done');
                }, 1600);
            };
            if (navigator.clipboard) {
                navigator.clipboard.writeText(text).then(done, function () {});
            }
        });
        pre.appendChild(btn);
    });

    // --- Tabs ---
    document.querySelectorAll('[data-tabs]').forEach(function (root) {
        var tabs = Array.prototype.slice.call(root.querySelectorAll('[role="tab"]'));
        function select(tab) {
            tabs.forEach(function (t) {
                var on = t === tab;
                t.setAttribute('aria-selected', on ? 'true' : 'false');
                t.tabIndex = on ? 0 : -1;
                document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
            });
        }
        tabs.forEach(function (tab, idx) {
            tab.addEventListener('click', function () { select(tab); });
            tab.addEventListener('keydown', function (e) {
                var step = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
                if (!step) return;
                var t = tabs[(idx + step + tabs.length) % tabs.length];
                select(t);
                t.focus();
            });
        });
    });

    // --- Expandable RFP rows ---
    document.querySelectorAll('.board-row').forEach(function (row) {
        row.tabIndex = 0;
        row.setAttribute('aria-expanded', 'false');
        function toggle() {
            var open = !row.classList.contains('is-open');
            row.classList.toggle('is-open', open);
            row.setAttribute('aria-expanded', open ? 'true' : 'false');
        }
        row.addEventListener('click', toggle);
        row.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggle();
            }
        });
    });

    // --- Mobile index drawer ---
    var sidebar = document.getElementById('sidebar');
    var toggleBtn = document.querySelector('.index-toggle');
    if (!sidebar || sidebar.hidden) toggleBtn.hidden = true;
    function setDrawer(open) {
        sidebar.classList.toggle('is-open', open);
        toggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
    toggleBtn.addEventListener('click', function () {
        setDrawer(!sidebar.classList.contains('is-open'));
    });
    sidebar.addEventListener('click', function (e) {
        if (e.target.closest('a')) setDrawer(false);
    });

    // --- Scrollspy ---
    var tocLinks = Array.prototype.slice.call(document.querySelectorAll('.toc a'));
    var targets = tocLinks.map(function (a) {
        return document.getElementById(a.getAttribute('href').slice(1));
    });
    function spy() {
        var line = window.innerHeight * 0.3;
        var active = -1;
        targets.forEach(function (t, idx) {
            if (t && t.getBoundingClientRect().top <= line) active = idx;
        });
        tocLinks.forEach(function (a, idx) {
            var on = idx === active;
            a.classList.toggle('is-active', on);
            if (on) a.setAttribute('aria-current', 'location');
            else a.removeAttribute('aria-current');
        });
    }
    window.addEventListener('scroll', spy, { passive: true });
    spy();

    // --- Search palette ---
    var palette = document.getElementById('palette');
    var input = document.getElementById('palette-input');
    var results = document.getElementById('palette-results');
    var index = [];
    function sectionOf(el) {
        var sec = el.closest('section.doc');
        var h = sec && sec.querySelector('h2');
        return h ? h.textContent.replace(/^#/, '').trim() : 'Manual';
    }
    document.querySelectorAll('.doc h2[id], .doc h3[id], .ref-group[id]').forEach(function (h) {
        index.push({ title: h.textContent.replace(/^#/, '').trim(), where: sectionOf(h), id: h.id, text: '' });
    });
    document.querySelectorAll('[data-search][id]').forEach(function (el) {
        var title = el.querySelector('code, .board-title, strong');
        index.push({
            title: title ? title.textContent : el.id,
            where: sectionOf(el),
            id: el.id,
            text: el.getAttribute('data-search')
        });
    });
    document.querySelectorAll('.faq details').forEach(function (d, n) {
        d.id = d.id || 'faq-' + (n + 1);
        index.push({ title: d.querySelector('summary').textContent, where: 'FAQ', id: d.id, text: d.textContent });
    });
    var selected = 0;
    var current = [];
    function render() {
        var q = input.value.trim().toLowerCase();
        var terms = q.split(/\s+/).filter(Boolean);
        current = index.filter(function (item) {
            var hay = (item.title + ' ' + item.text + ' ' + item.where).toLowerCase();
            return terms.every(function (t) { return hay.indexOf(t) !== -1; });
        }).sort(function (a, b) {
            var at = a.title.toLowerCase().indexOf(q) === -1 ? 1 : 0;
            var bt = b.title.toLowerCase().indexOf(q) === -1 ? 1 : 0;
            return at - bt;
        }).slice(0, 12);
        selected = 0;
        results.innerHTML = '';
        if (!current.length) {
            var li = document.createElement('li');
            li.className = 'empty';
            li.textContent = 'Nothing matches. Try a tool name, a route, or an RFP.';
            results.appendChild(li);
            input.removeAttribute('aria-activedescendant');
            return;
        }
        current.forEach(function (item, n) {
            var li = document.createElement('li');
            li.id = 'res-' + n;
            li.setAttribute('role', 'option');
            var a = document.createElement('a');
            a.href = '#' + item.id;
            a.tabIndex = -1;
            var strong = document.createElement('span');
            strong.textContent = item.title;
            var small = document.createElement('small');
            small.textContent = item.where;
            a.appendChild(strong);
            a.appendChild(small);
            a.addEventListener('click', function () { go(item); });
            li.appendChild(a);
            results.appendChild(li);
        });
        mark();
    }
    function mark() {
        Array.prototype.forEach.call(results.children, function (li, n) {
            li.setAttribute('aria-selected', n === selected ? 'true' : 'false');
            if (n === selected) li.scrollIntoView({ block: 'nearest' });
        });
        input.setAttribute('aria-activedescendant', 'res-' + selected);
    }
    var opener = null;
    function open() {
        opener = document.activeElement;
        palette.hidden = false;
        input.value = '';
        render();
        input.focus();
    }
    function close() {
        palette.hidden = true;
        if (opener && opener.focus) opener.focus();
    }
    function go(item) {
        palette.hidden = true;
        var el = document.getElementById(item.id);
        if (el && el.tagName === 'DETAILS') el.open = true;
        if (el && el.classList.contains('board-row') && !el.classList.contains('is-open')) el.click();
        location.hash = item.id;
    }
    document.querySelectorAll('[data-search-open]').forEach(function (b) {
        b.addEventListener('click', open);
    });
    input.addEventListener('input', render);
    input.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowDown') { e.preventDefault(); selected = Math.min(selected + 1, current.length - 1); mark(); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); selected = Math.max(selected - 1, 0); mark(); }
        else if (e.key === 'Enter' && current[selected]) { e.preventDefault(); go(current[selected]); }
        else if (e.key === 'Escape') { close(); }
    });
    palette.addEventListener('click', function (e) {
        if (e.target === palette) close();
    });
    document.addEventListener('keydown', function (e) {
        var typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName);
        if ((e.key === '/' && !typing) || (e.key.toLowerCase() === 'k' && (e.metaKey || e.ctrlKey))) {
            e.preventDefault();
            if (palette.hidden) open(); else close();
        } else if (e.key === 'Escape' && !sidebar.hidden && sidebar.classList.contains('is-open')) {
            setDrawer(false);
            toggleBtn.focus();
        }
    });
}());
