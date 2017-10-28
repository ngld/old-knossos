/*
 * blueimp Gallery YouTube Video Factory JS
 * https://github.com/blueimp/Gallery
 *
 * Copyright 2013, Sebastian Tschan
 * modified by ngld
 * https://blueimp.net
 *
 * Licensed under the MIT license:
 * https://opensource.org/licenses/MIT
 */

 /* global define, window, document, YT */


'use strict';

import Gallery from 'blueimp-gallery/js/blueimp-gallery.min.js';

Object.assign(Gallery.prototype.options, {
    // The list object property (or data attribute) with the YouTube video id:
    youTubeVideoIdProperty: 'youtube',
    // Optional object with parameters passed to the YouTube video player:
    // https://developers.google.com/youtube/player_parameters
    youTubePlayerVars: {
        wmode: 'transparent'
    },
    // Require a click on the native YouTube player for the initial playback:
    youTubeClickToPlay: true
});

let textFactory = Gallery.prototype.textFactory || Gallery.prototype.imageFactory;
let ytapi_loaded = false;

class YouTubePlayer {
    constructor(videoId, playerVars, clickToPlay) {
        this.videoId = videoId;
        this.playerVars = playerVars;
        this.clickToPlay = clickToPlay;
        this.element = document.createElement('div');
        this.listeners = {};
    }

    canPlayType() {
        return true;
    }

    on(type, func) {
        this.listeners[type] = func;
        return this;
    }

    loadAPI() {
        if(ytapi_loaded) return;
        ytapi_loaded = true;

        let onYouTubeIframeAPIReady = window.onYouTubeIframeAPIReady;
        window.onYouTubeIframeAPIReady = () => {
            if (onYouTubeIframeAPIReady) {
                onYouTubeIframeAPIReady.apply(this)
            }

            this.play();
        };

        let scriptTag = document.createElement('script');
        scriptTag.src = 'https://www.youtube.com/iframe_api';
        document.body.appendChild(scriptTag);
    }

    onReady() {
        this.ready = true;
        this.player.setPlaybackQuality('hd720');

        if(this.playOnReady) {
            this.play();
        }
    }

    onPlaying() {
        if(this.playStatus < 2) {
            this.listeners.playing();
            this.playStatus = 2;
        }
    }

    onPause() {
        Gallery.prototype.setTimeout.call(this, this.checkSeek, null, 300);
    }

    checkSeek() {
        if(this.stateChange === YT.PlayerState.PAUSED || this.stateChange === YT.PlayerState.ENDED) {
            // check if current state change is actually paused
            this.listeners.pause();
            delete this.playStatus;
        }
    }

    onStateChange(event) {
        switch (event.data) {
            case YT.PlayerState.PLAYING:
              this.hasPlayed = true;
              this.onPlaying();
              break;

            case YT.PlayerState.PAUSED:
            case YT.PlayerState.ENDED:
                this.onPause();
                break;
        }
    
        // Save most recent state change to this.stateChange
        this.stateChange = event.data;
    }

    onError(event) {
        this.listeners.error(event);
    }

    play() {
        if(!this.playStatus) {
            this.listeners.play();
            this.playStatus = 1;
        }

        if(this.ready) {
            this.player.playVideo();
        } else {
            this.playOnReady = true;
            if(!(window.YT && YT.Player)) {
                this.loadAPI();
            } else if(!this.player) {
                this.player = new YT.Player(this.element, {
                    videoId: this.videoId,
                    playerVars: this.playerVars,
                    events: {
                        onReady: () => {
                            this.onReady();
                        },
                        
                        onStateChange: (event) => {
                            this.onStateChange(event)
                        },

                        onError: (event) => {
                            this.onError(event)
                        }
                    }
                });
            }
        }
    }

    pause() {
        if(this.ready) {
            this.player.pauseVideo();
        } else if (this.playStatus) {
            delete this.playOnReady;
            this.listeners.pause();
            delete this.playStatus;
        }
    }
}

Object.assign(Gallery.prototype, {
    YouTubePlayer: YouTubePlayer,

    textFactory: function (obj, callback) {
        let options = this.options
        let videoId = this.getItemProperty(obj, options.youTubeVideoIdProperty)
        if(videoId) {
            if(this.getItemProperty(obj, options.urlProperty) === undefined) {
                obj[options.urlProperty] = 'https://www.youtube.com/watch?v=' + videoId;
            }
            
            if(this.getItemProperty(obj, options.videoPosterProperty) === undefined) {
                obj[options.videoPosterProperty] = 'https://img.youtube.com/vi/' + videoId + '/maxresdefault.jpg';
            }

            return this.videoFactory(
                obj,
                callback,
                new YouTubePlayer(
                    videoId,
                    options.youTubePlayerVars,
                    options.youTubeClickToPlay
                )
            );
        }

        return textFactory.call(this, obj, callback);
    }
});

