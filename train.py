import numpy as np
import torch
import torchvision
import torchvision.transforms as transforms
from datetime import datetime
import os
from utils import train_model, eval_model, SmoothedDataset
from attack_lib import attack_setting

import argparse
 
parser = argparse.ArgumentParser()
# Dataset Setting
parser.add_argument('--dataset', type=str, default='mnist')
parser.add_argument('--pair_id', type=int, default=0)

# Trojan Attack Setting
parser.add_argument('--atk_method', type=str, default='onepixel')
parser.add_argument('--poison_r', type=float, default=0.0)
parser.add_argument('--delta', type=float, default=1.0)

# Smoothing Setting
#parser.add_argument('--N_m', type=int, default=1000)
parser.add_argument('--N_m', type=int, default=10)
parser.add_argument('--sigma', type=float, default=0.0)
parser.add_argument('--dldp_sigma', type=float, default=0.0)
parser.add_argument('--dldp_gnorm', type=float, default=5.0)

if __name__ == '__main__':
    args = parser.parse_args()
    args = vars(args)
    print (args)

    use_gpu = True

    poisoned_train, testloader_benign, testloader_poison, BATCH_SIZE, N_EPOCH, LR, Model = attack_setting(args)

    binary_str = 'binary'
    if args['pair_id'] != 0:
        binary_str = binary_str+'(%d)'%(args['pair_id']+1)
    PREFIX = './saved_model/%s%s-%s(%.4f)-pr%.4f-sigma%.4f-N_m%d'%(args['dataset'], binary_str, args['atk_method'], args['delta'], args['poison_r'], args['sigma'], args['N_m'])
    if args['dldp_sigma'] != 0:
        dlpargs = '-dldp(%s,%s)'%(args['dldp_sigma'], args['dldp_gnorm'])
        PREFIX = PREFIX+ dlpargs

    if not os.path.isdir(PREFIX):
        os.makedirs(PREFIX)

    filename = './logs/%s-%s-delta%.4f-sigma%.4f-poison_r%.4f-n_m%d.csv'%(args['dataset'], args['atk_method'], args['delta'], args['sigma'],args['poison_r'], args['N_m'])
    if args['dldp_sigma'] != 0:
        dlpargs = '-dldp(%s,%s)'%(args['dldp_sigma'], args['dldp_gnorm'])
        filename = filename + dlpargs

    if not os.path.isdir('./logs'):
        os.makedirs('./logs')
    with open(filename, 'w') as f: 
        f.write("N, Benign, Poison\n")
        for n in range(args['N_m']):
            model = Model(gpu=use_gpu)
            trainset = SmoothedDataset(poisoned_train, args['sigma'])
            trainloader = torch.utils.data.DataLoader(trainset, batch_size=BATCH_SIZE, shuffle=True)
            train_model(model, trainloader, lr=LR, epoch_num=N_EPOCH, dldp_setting=(args['dldp_sigma'],args['dldp_gnorm']), verbose=False)
            save_path = PREFIX+'/smoothed_%d.model'%n
            torch.save(model.state_dict(), save_path)
            acc_benign = eval_model(model, testloader_benign)
            acc_poison = eval_model(model, testloader_poison)
            print ("%d - Benign/Poison ACC %.4f/%.4f, saved to %s @ %s"%(n, acc_benign, acc_poison, save_path, datetime.now()))
            f.write(f"{n}, {acc_benign}, {acc_poison}\n")
