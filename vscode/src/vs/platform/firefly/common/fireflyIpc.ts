import { Event } from '../../../base/common/event.js';
import { IChannel, IServerChannel } from '../../../base/parts/ipc/common/ipc.js';
import { IFireflyMainService, IFireflyStatus } from './firefly.js';

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
            case 'setAutonomousMode': return Promise.resolve(this.service.setAutonomousMode(arg));
            case 'sendIntent': return Promise.resolve(this.service.sendIntent(arg.id, arg.args));
            case 'createAgent': return this.service.createAgent(arg.name, arg.persona);
            case 'deleteAgent': return this.service.deleteAgent(arg.id);
            case 'setSafetyMode': return Promise.resolve(this.service.setSafetyMode(arg));
            case 'setActiveModel': return Promise.resolve(this.service.setActiveModel(arg));
            case 'sendChat': return Promise.resolve(this.service.sendChat(arg));
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

    setAutonomousMode(enabled: boolean): Promise<void> {
        return this.channel.call('setAutonomousMode', enabled);
    }

    sendIntent(id: string, args: any[]): Promise<void> {
        return this.channel.call('sendIntent', { id, args });
    }

    createAgent(name: string, persona: string): Promise<string> {
        return this.channel.call('createAgent', { name, persona });
    }

    deleteAgent(id: string): Promise<void> {
        return this.channel.call('deleteAgent', { id });
    }

    setSafetyMode(mode: string): Promise<void> {
        return this.channel.call('setSafetyMode', mode);
    }

    setActiveModel(modelId: string): Promise<void> {
        return this.channel.call('setActiveModel', modelId);
    }

    sendChat(text: string): Promise<void> {
        return this.channel.call('sendChat', text);
    }
}
