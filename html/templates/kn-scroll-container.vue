<script>
export default {
    props: {
        dummy: {
            required: false
        }
    },

    data: () => ({
        scroll: 0,
        listener: null
    }),

    created() {
        this.listener = () => this.$forceUpdate();
        window.addEventListener('resize', this.listener);
    },

    beforeDestroy() {
        window.removeEventListener('resize', this.listener);
    },

    activated() {
        this.$refs.container.scrollTop = this.scroll;
    }
};
</script>
<template>
	<div class="main-container scroll-style" ref="container" @scroll.stop="scroll = $refs.container.scrollTop">
	    <div class="main-background"></div>
	    <slot :update="() => $nextTick(() => $forceUpdate())"></slot>
	    <div class="main-shadow-effect" :style="{ width: $refs.container ? $refs.container.clientWidth + 'px' : 'auto' }"></div>
	</div>
</template>