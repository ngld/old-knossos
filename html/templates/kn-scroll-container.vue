<script>
export default {
    data: () => ({
        scroll: 0
    }),

    activated() {
        this.$refs.container.scrollTop = this.scroll;
    }
};
</script>
<template>
	<div class="main-container scroll-style" ref="container" @scroll.stop="scroll = $refs.container.scrollTop">
	    <div class="main-background"></div>
	    <slot></slot>
	    <div class="main-shadow-effect"></div>
	</div>
</template>