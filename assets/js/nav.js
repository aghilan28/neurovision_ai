/* =========================================================================
 * NeuroVision Shared Navigation / Auth / Active State Script
 * - Renders the sidebar dynamically only if a [data-nav] container exists.
 * - Determines active item from window.location.pathname (no hardcoding).
 * - Provides signOut(), requireAuth(), applyProfile() and an initPage() helper.
 * - Logout clears ALL session keys and returns to landing page (/).
 * - Preserves existing UI styling exactly.
 * ========================================================================= */
(function(global){
  'use strict';

  var SESSION_KEY = 'nv_session';
  var USER_KEY    = 'nv_session_user';
  var ROLE_KEY    = 'nv_session_role';
  var NAME_KEY    = 'nv_profile_name';
  var INST_KEY    = 'nv_profile_institution';

  var NAV_ITEMS = [
    { href: '/dashboard', icon: 'dashboard',     label: 'Dashboard' },
    { href: '/upload',    icon: 'upload_file',   label: 'Upload EEG' },
    { href: '/patients',  icon: 'folder_shared', label: 'Patient Records' },
    { href: '/export',    icon: 'ios_share',     label: 'Export Center' },
    { href: '/status',    icon: 'analytics',     label: 'System Status' },
    { href: '/settings',  icon: 'settings',      label: 'Settings' }
  ];

  /* --------------------------------------------------------------------- */
  function readSession(){
    try{
      var raw = localStorage.getItem(SESSION_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (parsed && (parsed.token || parsed.access_token)) return parsed;
      // Legacy: plain string token
      return { token: raw, user: {
        name: localStorage.getItem(NAME_KEY) || 'Clinician',
        role: localStorage.getItem(ROLE_KEY) || 'clinician',
        institution: localStorage.getItem(INST_KEY) || '',
        email: localStorage.getItem(USER_KEY) || ''
      }};
    }catch(e){
      var raw2 = localStorage.getItem(SESSION_KEY);
      if (raw2) return { token: raw2, user: {
        name: localStorage.getItem(NAME_KEY) || 'Clinician',
        role: localStorage.getItem(ROLE_KEY) || 'clinician',
        institution: '', email: ''
      }};
      return null;
    }
  }

  function isAuthenticated(){
    var s = readSession();
    return !!(s && (s.token || s.access_token));
  }

  function requireAuth(redirect){
    if (!isAuthenticated()){
      var dest = redirect || '/auth';
      window.location.replace(dest);
      return false;
    }
    return true;
  }

  function redirectIfAuthed(dest){
    if (isAuthenticated()){
      window.location.replace(dest || '/dashboard');
      return true;
    }
    return false;
  }

  function clearSession(){
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(ROLE_KEY);
    localStorage.removeItem(NAME_KEY);
    localStorage.removeItem(INST_KEY);
  }

  function signOut(){
    clearSession();
    window.location.href = '/';
  }

  function initials(name){
    if (!name) return 'NV';
    return name.split(/\s+/).filter(Boolean).map(function(s){return s[0];}).slice(0,2).join('').toUpperCase();
  }

  function applyProfile(){
    var s = readSession();
    var u = (s && s.user) || {};
    var name  = u.name  || localStorage.getItem(NAME_KEY)  || u.email || localStorage.getItem(USER_KEY) || 'Clinician';
    var role  = u.role  || localStorage.getItem(ROLE_KEY)  || 'clinician';
    var inst  = u.institution || localStorage.getItem(INST_KEY) || 'Neuro-AI Lab';
    var email = u.email || localStorage.getItem(USER_KEY) || '';

    var pName = document.getElementById('profile-name');
    if (pName) pName.textContent = name;
    var pRole = document.getElementById('profile-role');
    if (pRole) pRole.textContent = role.toUpperCase() === 'CLINICIAN' ? 'Senior Neurologist' : role;
    var pInst = document.getElementById('profile-institution');
    if (pInst) pInst.textContent = inst;
    var avatar = document.getElementById('profile-avatar');
    if (avatar){
      avatar.textContent = initials(name);
      avatar.style.background = 'rgba(79,55,138,0.25)';
      avatar.style.color = '#cfbcff';
    }
  }

  /* ---- Active-route detection (dynamic, no hardcoded classes) ----------- */
  function normalizePath(p){
    p = (p || '').replace(/\/+$/,'') || '/';
    return p;
  }

  function isActive(href){
    var path = normalizePath(window.location.pathname);
    var h    = normalizePath(href);
    if (path === h) return true;
    // /analysis/<id> is the clinical report (workflow child of upload) but we
    // do NOT mark any sidebar item active on the report view — it's a dedicated
    // report screen reached from the upload wizard.
    if (path.indexOf('/analysis/') === 0) return false;
    return false;
  }

  function buildSidebar(){
    var hosts = document.querySelectorAll('[data-nav]');
    if (!hosts.length) return;
    var html = '';
    NAV_ITEMS.forEach(function(item){
      var active = isActive(item.href);
      var baseCls = 'flex items-center gap-3 px-4 py-3 transition-all duration-150 text-sm font-medium';
      var cls;
      if (active){
        cls = baseCls + ' bg-surface-container-high text-primary border-l-2 border-primary';
      } else {
        cls = baseCls + ' text-on-surface-variant hover:bg-surface-container-highest hover:text-on-surface';
      }
      html += '<a class="'+cls+'" href="'+item.href+'">'+
              '<span class="material-symbols-outlined text-[20px]">'+item.icon+'</span>'+
              '<span>'+item.label+'</span>'+
              '</a>';
    });
    hosts.forEach(function(el){ el.innerHTML = html; });
  }

  /* ---- initPage helper ------------------------------------------------- */
  function initPage(opts){
    opts = opts || {};
    if (opts.requireAuth){
      if (!requireAuth(opts.authRedirect || '/auth')) return;
    }
    if (opts.guestOnly){
      if (redirectIfAuthed(opts.authedRedirect || '/dashboard')) return;
    }
    buildSidebar();
    applyProfile();
    if (typeof opts.after === 'function') opts.after();
  }

  /* Expose */
  global.NV = global.NV || {};
  global.NV.readSession     = readSession;
  global.NV.isAuthenticated = isAuthenticated;
  global.NV.requireAuth     = requireAuth;
  global.NV.redirectIfAuthed= redirectIfAuthed;
  global.NV.signOut         = signOut;
  global.NV.clearSession    = clearSession;
  global.NV.applyProfile    = applyProfile;
  global.NV.buildSidebar    = buildSidebar;
  global.NV.isActive        = isActive;
  global.NV.initPage        = initPage;

  /* Auto-wire any existing .nv-signout buttons */
  document.addEventListener('DOMContentLoaded', function(){
    document.querySelectorAll('[data-signout], .nv-signout').forEach(function(b){
      b.addEventListener('click', function(e){ e.preventDefault(); signOut(); });
    });
  });

})(window);
