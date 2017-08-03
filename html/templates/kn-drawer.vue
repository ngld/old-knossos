<script>
export default {
    props: ['label'],

    data: () => ({
        open: false
    })
};
</script>
<template>
    <div class="kn-drawer">
        <div class="title" @click="open = !open">
            <div class="text">{{ label }}</div>
            <div class="line"></div>
            <i :class="{ fa: true, 'fa-chevron-down': !open, 'fa-chevron-up': open }"></i>
        </div>
        <div class="content-wrapper">
            <div :class="{ content: true, open: open }">
                <slot></slot>
            </div>
        </div>
    </div>
</template>