if(window.qt) {
    new QWebChannel(qt.webChannelTransport, function (channel) {
        window.fs2mod = channel.objects.fs2mod;

        fs2mod.isFs2PathSet(function (res) {
            if(!res) {
                $('#install-note').removeClass('hide');

                $('#sel-fso').click(function (e) {
                    e.preventDefault();
                    fs2mod.selectFs2path();
                });
                $('#gog-install').click(function (e) {
                    e.preventDefault();
                    fs2mod.runGogInstaller();
                });

                $('#tc-install').click(function (e) {
                    e.preventDefault();
                    // Um... this is mean.
                    fs2mod.selectFs2path();
                });
            } else {    
                location.href = 'modlist.html';
            }
        });
    });
} else {
    $(function () {
        var res = fs2mod.isFs2PathSet();
        if(!res) {
            $('#install-note').removeClass('hide');

            $('#sel-fso').click(function (e) {
                e.preventDefault();
                fs2mod.selectFs2path();
            });
            $('#gog-install').click(function (e) {
                e.preventDefault();
                fs2mod.runGogInstaller();
            });

            $('#tc-install').click(function (e) {
                e.preventDefault();
                // Um... this is mean.
                fs2mod.selectFs2path();
            });
        } else {    
            location.href = 'modlist.html';
        }
    });
}