import { Event } from '../../../base/common/event.js';
import { IChannel, IServerChannel } from '../../../base/parts/ipc/common/ipc.js';
import { IFireflyMainService, IFireflyStatus } from '../electron-main/firefly.js';

export class FireflyChannel implements IServerChannel {

    constructor(private service: IFireflyMainService) { }

    listen(_: unknown, event: string): Event<any> {
        switch (event) {
            case 'onDidStatusChange': return this.service.onDidChangeStatus;
        }

        throw new Error(`Event not found: ${event}`);
    }

    call(_: unknown, command: string, arg?: any): Promise<any> {
        switch (command) {
            case 'getStatus': return Promise.resolve(this.service.getStatus());
        }

        throw new Error(`Command not found: ${command}`);
    }
}

export class FireflyChannelClient {

    constructor(private channel: IChannel) { }

    get onDidStatusChange(): Event<IFireflyStatus> {
        return this.channel.listen('onDidStatusChange');
    }

    getStatus(): Promise<IFireflyStatus> {
        return this.channel.call('getStatus');
    }
}
