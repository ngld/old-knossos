(function () {
    function force_redraw(el) {
      var t = el.ownerDocument.createTextNode(' ');
      el.appendChild(t);
      setTimeout(function() { el.removeChild(t); }, 0);
    }

    function render_row(mvs, type) {
        var row = $('<div class="mod">');
        var mod;

        if($.isArray(mvs)) {
            mod = mvs[0];
        } else {
            mod = mvs;
            mvs = [mod];
        }

        if(type == 'available') {
            row.html($('#tpl-avail-mod').html());

            row.find('.install-btn').click(function (e) {
                e.preventDefault();

                fs2mod.install(mod.id, mod.version);
            });
        } else if(type == 'installed') {
            row.html($('#tpl-installed-mod').html());

            row.find('.run-btn').click(function (e) {
                e.preventDefault();

                fs2mod.runMod(mod.id, mod.version);
            });
            row.find('.settings-btn').click(function (e) {
                e.preventDefault();

                fs2mod.showSettings(mod.id, mod.version);
            });
            row.find('.del-btn').click(function (e) {
                e.preventDefault();

                fs2mod.uninstall(mod.id, mod.version);
            });
        } else if(type == 'downloading') {
            row.html($('#tpl-dl-mod').html());
            row.find('progress').attr('id', 'mod-prg-' + mod.id);

            row.find('.noop-btn').click(function (e) {
                e.preventDefault();
            });
            row.find('.abort-btn').click(function (e) {
                e.preventDefault();

                fs2mod.abortDownload(mod.id, mod.version);
            });
        } else if(type == 'updates') {
            row.html($('#tpl-update-mod').html());

            row.find('.update-btn').click(function (e) {
                e.preventDefault();

                fs2mod.updateMod(mod.id, mod.version);
            });
        }

        row.find('.title').text(mod.title);
        return row;
    }

    function update_mods(mods, type) {
        $('#loading').hide();

        var names = [];
        var mod_list = $('#mods').html('');

        $.each(mods, function (mid, info) {
            names.push([mid, info[0].title]);
        });

        names.sort(function (a, b) {
            return a[1] > b[1] ? 1 : (a[1] < b[1] ? -1 : 0);
        });

        names.forEach(function (item) {
            var mod = mods[item[0]];
            mod_list.append(render_row(mod, type));
        });
    }

    function update_progress(id, percent, text) {
        var prg_bar = $('#mod-prg-' + id);
        if(prg_bar.length == 0) return;

        var label = prg_bar.parent().find('.prg-label');
        prg_bar.attr('value', percent * 100);
        
        if(text == '') {
            label.html('<div style="visibility:hidden;">' + Math.random() + '</div>');
        } else {
            label.text(text);
        }
    }

    $(function () {
        fs2mod.updateModlist.connect(update_mods);
        fs2mod.modProgress.connect(update_progress);
    });
})();