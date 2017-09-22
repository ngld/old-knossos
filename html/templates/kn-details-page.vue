<script>
export default {
	props: ['mod']
}
</script>
<template>
	<div>
		<div class="img-frame">
		    <div class="title-frame">
		        <h1>{{ mod.title }}</h1>
		        Version <span>{{ mod.version }}</span>
		        <!-- TODO: version select (?) -->
		    </div>
		</div>

		<div class="row">
		    <div class="col-sm-6">
		        <kn-mod-buttons :tab="'details'" :mod="mod"></kn-mod-buttons>
		    </div>

		    <div class="col-sm-6 short-frame">
		        <button class="link-btn btn-link-red" v-if="mod.release_thread" @click="openLink(mod.release_thread)"><span class="btn-text">FORUM</span></button>
		        <button class="link-btn btn-link-blue" v-if="mod.videos.length > 0" @click="showVideos(mod.videos)"><span class="btn-text">VIDEOS</span></button>

		        <div class="date-frame pull-right">
		            <div v-if="mod.first_release">Release: {{ mod.first_release }}</div>
		            <div v-if="mod.last_update"><em>Last Updated: {{ mod.last_update }}</em></div>
		        </div>
		    </div>
		</div>

		<p v-html="mod.description"></p>
	</div>
</template>