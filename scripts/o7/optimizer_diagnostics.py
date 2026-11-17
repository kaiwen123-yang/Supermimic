"""Detached checkpoint summaries of actual parameters and optimizer groups."""
from __future__ import annotations

import inspect
import math
import torch
from torch import nn


def scalar(value):
    if isinstance(value, torch.Tensor):
        return value.detach().item()
    if isinstance(value, (list, tuple)):
        return [scalar(v) for v in value]
    return value


def norm_rows(parameters, metadata, initial):
    rows = []
    for key, parameter in parameters.items():
        value = parameter.detach().double()
        norm = float(torch.linalg.vector_norm(value))
        base = initial.get(key, norm)
        initial.setdefault(key, base)
        rows.append({**metadata[key], 'Frobenius_norm': norm,
                     'RMS': norm / math.sqrt(parameter.numel()),
                     'relative_to_initial': norm / base if base else None})
    groups = {}
    for row in rows:
        key = row['network'] + '/' + row['parameter_kind']
        group = groups.setdefault(key, {'numel': 0, 'tensor_count': 0, 'sum_squared_norm': 0.0})
        group['numel'] += row['numel']
        group['tensor_count'] += 1
        group['sum_squared_norm'] += row['Frobenius_norm'] ** 2
    for group in groups.values():
        group['Frobenius_norm'] = math.sqrt(group['sum_squared_norm'])
        group['RMS'] = math.sqrt(group['sum_squared_norm'] / group['numel'])
    return {'parameters': rows, 'groups': groups,
            'scope': 'learnable parameter objects, including temporarily frozen WM; excludes normalizer buffers',
            'norm_definition': 'L2 over every tensor element; Frobenius for matrices',
            'zero_initial_norm_ratio': None}


class OptimizerDiagnostics:
    def __init__(self, runner):
        self.networks = {
            'wm': (runner._wm.dynamics, runner.world_model_learner.optimizers),
            'actor': (runner.policy_learner.actor, runner.policy_learner.actor_optimizers),
            'critic': (runner.policy_learner.critic, runner.policy_learner.critic_optimizers)}
        self.parameters, self.metadata, self.initial = {}, {}, {}
        for network, (module, optimizers) in self.networks.items():
            hidden = {id(linear.weight) for seq in module.modules() if isinstance(seq, nn.Sequential)
                      for linear in [m for m in seq if isinstance(m, nn.Linear)][1:-1]}
            owners = {id(p): (path, sub, local_name) for path, sub in module.named_modules()
                      for local_name, p in sub.named_parameters(recurse=False)}
            membership = {id(p): {'optimizer_index': i, 'group_index': j, 'type': type(opt).__name__}
                          for i, opt in enumerate(optimizers) for j, group in enumerate(opt.param_groups)
                          for p in group['params']}
            for name, parameter in module.named_parameters():
                path, owner, local_name = owners[id(parameter)]
                if id(parameter) in hidden:
                    kind = 'official_Muon_inner_Linear_weights'
                elif isinstance(owner, nn.LayerNorm):
                    kind = 'LayerNorm_affine'
                elif local_name == 'bias':
                    kind = 'biases'
                elif isinstance(owner, nn.Linear) and local_name == 'weight':
                    kind = 'first_last_Linear_weights'
                else:
                    kind = 'other_parameters'
                key = network + '/' + name
                self.parameters[key] = parameter
                self.metadata[key] = {'network': network, 'parameter_name': name,
                    'shape': list(parameter.shape), 'numel': parameter.numel(), 'parameter_kind': kind,
                    'owner_module': path, 'owner_type': type(owner).__name__,
                    'optimizer_group': membership[id(parameter)]}

    def optimizer_metadata(self):
        result = {}
        for network, (module, optimizers) in self.networks.items():
            names = {id(p): name for name, p in module.named_parameters()}
            result[network] = []
            for opt in optimizers:
                groups = []
                for group in opt.param_groups:
                    params = [{'name': names[id(p)], 'shape': list(p.shape), 'numel': p.numel()}
                              for p in group['params']]
                    groups.append({'hyperparameters': {k: scalar(v) for k, v in group.items() if k != 'params'},
                        'parameters': params, 'parameter_count': len(params),
                        'numel': sum(p['numel'] for p in params), 'effective_lr': scalar(group['lr']),
                        'lr_storage': 'device_tensor' if torch.is_tensor(group['lr']) else 'python_float'})
                result[network].append({'type': type(opt).__module__ + '.' + type(opt).__name__, 'groups': groups})
        return result

    def provenance(self):
        return {'version': torch.__version__, 'module_path': torch.__file__,
                'optimizer_implementations': {name: {'path': inspect.getfile(cls), 'signature': str(inspect.signature(cls))}
                    for name, cls in [('Adam', torch.optim.Adam), ('Muon', torch.optim.Muon)]}}

    def snapshot(self):
        return {**norm_rows(self.parameters, self.metadata, self.initial),
                'optimizers': self.optimizer_metadata()}
