function list_mods() {
    if(!fs2mod.isFs2PathSet()) return;
    $('#install-note').hide();

    var mod_list = $('#mod-list').empty();
    var update_link = $('<a href="#">Update mod list</a>');
    var table = $('<table class="table">');
    var mods = fs2mod.getInstalledMods();

    if(mods.length > 0) {
        console.log(mods);
        $.each(mods, function (i, mod) {
            var row = $('<tr>');

            var logo = $('<td>').appendTo(row);
            var title = $('<td>').appendTo(row);

            var recent = fs2mod.query(mod.id);
            var has_update = fs2mod.vercmp(recent.version, mod.version) > 0;

            if(mod.logo) {
                logo.append($('<img class="mod-logo">').attr('src', 'fsrs:///logo/' + mod.id + '/' + mod.version));
                logo.append('&nbsp;');
            }
            title.append($('<span>').text(mod.title + ' (' + mod.version + ')'));

            var actions = $('<div class="mod-actions">');
            actions.append($('<a href="#">Launch</a>').click(function (e) {
                e.preventDefault();
                fs2mod.runMod(mod.id, '==' + mod.version);
            }));
            actions.append(' | ').append($('<a href="#">Settings</a>').click(function (e) {
                e.preventDefault();
                fs2mod.showSettings(mod.id);
            }));

            if(has_update) {
                title.append('<br><strong>Update available!</strong>');
                actions.append(' | ').append($('<a href="#">Update</a>').click(function (e) {
                    e.preventDefault();
                    var my_pkgs = [];
                    $.each(mod.packages, function (i, pkg) {
                        my_pkgs.push(pkg.name);
                    });

                    fs2mod.install(mod.id, null, my_pkgs);
                }));
            }

            title.append(actions)
            table.append(row);
        });

        mod_list.html(update_link).append('<br><br>').append(table);
    } else {
        mod_list.html(update_link).append('<br><hr>No mods found!');
    }

    update_link.click(function (e) {
        e.preventDefault();

        fs2mod.fetchModlist();
    });
}

$(function () {
    fs2mod.repoUpdated.connect(list_mods);

    if(!fs2mod.isFs2PathSet()) {
        $('#install-note').removeClass('hide');

        $('#sel-fso').click(function (e) {
            e.preventDefault();
            fs2mod.selectFs2path();
        });
        $('#gog-install').click(function (e) {
            e.preventDefault();
            fs2mod.runGogInstaller();
        });
    } else {    
        list_mods();
    }
});