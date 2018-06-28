<style scoped>
    .save-btn-cont {
        display: inline-block;
        min-height: 52px;
    }

    .save-form {
        display: inline-block;
        margin-right: 20px;
    }

    .success-save {
        display: inline-block;
        padding: 10px;
        font-size: x-large;
        color: green;
        text-shadow: 2px 2px black;
    }

    .save-fade-leave-active {
        transition: opacity 1.3s;
    }

    .save-fade-leave {
        opacity: 1;
    }

    .save-fade-leave-to {
        opacity: 0;
    }
</style>
<script>
export default {
    props: ['save_handler'],

    data: () => ({
        show_notice: false
    }),

    methods: {
        triggerSave() {
            let result = this.save_handler();
            if(result.then) {
                result.then(this.handleResult.bind(this));
            } else {
                this.handleResult(result);
            }
        },

        handleResult(result) {
            if(result) this.showNotice();
        },

        showNotice() {
            this.show_notice = true;
            this.$nextTick(() => this.show_notice = false);
        }
    }
}
</script>
<template>
    <div class="save-btn-cont">
        <div class="form-group save-form">
            <div>
                <button class="mod-btn btn-green save-btn" @click.prevent="triggerSave">
                    <span class="btn-text">SAVE</span>
                </button>
            </div>
        </div>
        <transition name="save-fade" v-if="show_notice">
            <div class="success-save">
                <span>Saved!</span>
            </div>
        </transition>
    </div>
</template>
