<script>
export default {
	props: ['mod'],

	data: () => ({
		version: null
	}),

	created() {
		this.version = this.mod.version;
	},

	computed: {
		cur_mod() {
			for(let mod of this.mod.versions) {
				if(mod.version === this.version) {
					return Object.assign(mod, {
						status: this.mod.status,
						progress: this.mod.progress,
						progress_info: this.mod.progress_info
					});
				}
			}

			return null;
		}
	},

	methods: {
		openLink(url) {
			fs2mod.openExternal(url);
		},

		showVideos(videos) {
			alert('Not implemented yet!');
		}
	}
}
</script>
<template>
	<div>
		<div class="img-frame">
			<img v-if="mod.banner" :src="mod.banner.indexOf('://') === -1 ? 'file://' + mod.banner : mod.banner" class="mod-banner">
		    <div class="title-frame">
		        <h1>{{ mod.title }}</h1>
		        Version
		        <select v-model="version" class="form-control">
		        	<option v-for="m in mod.versions" :value="m.version">{{ m.version }}</option>
		        </select>
		    </div>
		</div>

		<div class="row">
		    <div class="col-sm-6">
		        <kn-mod-buttons :tab="'details'" :mod="cur_mod"></kn-mod-buttons>
		    </div>

		    <div class="col-sm-6 short-frame">
		        <button class="link-btn btn-link-red" v-if="cur_mod.release_thread" @click="openLink(cur_mod.release_thread)"><span class="btn-text">FORUM</span></button>
		        <button class="link-btn btn-link-blue" v-if="cur_mod.videos.length > 0" @click="showVideos(cur_mod.videos)"><span class="btn-text">VIDEOS</span></button>

		        <div class="date-frame pull-right">
		            <div v-if="cur_mod.first_release">Release: {{ cur_mod.first_release }}</div>
		            <div v-if="cur_mod.last_update"><em>Last Updated: {{ cur_mod.last_update }}</em></div>
		        </div>
		    </div>
		</div>

		<p v-html="cur_mod.description"></p>
	</div>
</template>