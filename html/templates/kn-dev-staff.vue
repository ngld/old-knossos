<script>
export default {
    props: ['mid'],

    components: {
        'kn-save-btn': require('./kn-save-btn.vue').default
    },

    data: () => ({
        loading: false,
        error: null,
        members: []
    }),

    created() {
        this.loading = true;

        call_async(fs2mod.getTeamMembers, this.mid, (resp) => {
            this.loading = false;
            if(!resp.result) {
                switch(resp.reason) {
                    case 'missing':
                        this.error = "The mod wasn't found on Nebula. You can only modify members of uploaded mods.";
                        break;

                    case 'unauthorized':
                        this.error = "You are not allowed to edit team members and can't view them due to this.";
                        break;

                    case 'no login':
                        this.error = "You aren't logged in. Please go to the settings page and login.";
                        break;

                    default:
                        this.error = "An unexpected error ocurred!";
                        break;
                }

                this.members = [];
            } else {
                this.members = resp.members;
            }
        });
    },

    methods: {
        save() {
            return call_async_promise(fs2mod.updateTeamMembers, this.mid, JSON.stringify(this.members));
        },

        addRow() {
            this.members.push({
                user: "",
                role: 20
            });
        },

        delRow(i) {
            this.members.splice(i, 1);
        }
    }
}
</script>
<template>
    <div>
        <div v-if="error" class="alert alert-danger">
            {{ error }}
        </div>

        <table class="table">
            <thead>
                <tr>
                    <td>User</td>
                    <td>Role</td>
                    <td></td>
                </tr>
            </thead>
            <tbody>
                <tr v-if="loading">
                    <td>Loading...</td>
                    <td> </td>
                </tr>
                <tr v-else v-for="(mem, i) in members">
                    <td><input type="text" class="form-control" v-model="mem.user"></td>
                    <td>
                        <select class="form-control" v-model="mem.role" style="min-width: 100px">
                            <option :value="0">Owner</option>
                            <option :value="10">Manager</option>
                            <option :value="20">Uploader</option>
                            <option :value="30">Tester</option>
                        </select>
                    </td>
                    <td>
                        <button class="mod-btn btn-link-red" @click.prevent="delRow(i)"><i class="fa fa-times"></i></button>
                    </td>
                </tr>
            </tbody>

            <br>
            <button v-if="!error" class="mod-btn btn-blue" @click.prevent="addRow">
                <span class="btn-text">Add Member</span>
            </button>
            <kn-save-btn :save-handler="save" v-if="!error" />

            <div style="margin-top:120px;">
                <hr>

                Here's a short explanation of the available roles:
                <ul>
                    <li><strong>Tester</strong>: Can only download &amp; install the mod <em>(only relevant for private mods)</em></li>
                    <li><strong>Uploader</strong>: Same permissions as Tester. Can also upload releases and edit metadata.</li>
                    <li><strong>Manager</strong>: Same permissions as Uploader. Can also add and remove staff members but can't remove or add Owners.</li>
                    <li><strong>Owner</strong>: Same as Manager but can also add or remove Owners.</li>
                </ul>
            </div>
        </table>
    </div>
</template>