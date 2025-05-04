import torch
import torch.nn as nn

class DeepStackModel(nn.Module):
    def __init__(self, input_dim, output_dim, hidden_units=64):
        super(DeepStackModel, self).__init__()
        # Expanded to 7 fully-connected hidden layers
        self.fc1 = nn.Linear(input_dim, hidden_units)
        self.fc2 = nn.Linear(hidden_units, hidden_units)
        self.fc3 = nn.Linear(hidden_units, hidden_units)
        self.fc4 = nn.Linear(hidden_units, hidden_units)
        self.fc5 = nn.Linear(hidden_units, hidden_units)
        self.fc6 = nn.Linear(hidden_units, hidden_units)
        self.fc7 = nn.Linear(hidden_units, hidden_units)
        # Output layer
        self.out = nn.Linear(hidden_units, output_dim)
        # Use ReLU for efficiency
        self.relu = nn.ReLU()
        
        # Initialize with smaller weights to avoid exploding gradients
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.relu(self.fc3(x))
        x = self.relu(self.fc4(x))
        x = self.relu(self.fc5(x))
        x = self.relu(self.fc6(x))
        x = self.relu(self.fc7(x))
        out = self.out(x)
        return out

# Helper function to create appropriate models for flop and turn
def create_flop_model(hidden_units=64):
    # Flop: 1 (pot) + 3*52 (cards) = 157 inputs, 1176 outputs
    return DeepStackModel(input_dim=157, output_dim=1176, hidden_units=hidden_units)

def create_turn_model(hidden_units=64):
    # Turn: 1 (pot) + 4*52 (cards) = 209 inputs, 1128 outputs
    return DeepStackModel(input_dim=209, output_dim=1128, hidden_units=hidden_units)