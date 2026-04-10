import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, models, transforms
from torch.utils.data import DataLoader, random_split
import matplotlib.pyplot as plt
import time

# --- CONFIGURATION FOR LOW-SPEC PC ---
BATCH_SIZE = 8        # Small batch size to save RAM
EPOCHS = 5            # Reduced epochs for faster results
LEARNING_RATE = 0.0001
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")# Forced CPU usage
DATA_DIR = 'D:\\College\\Sem 6\\Deep Learning\\EXP 6\\Cow Breed Dataset' # Update this to your folder path

# --- 1. DATA PREPROCESSING ---
# EfficientNet_B0 usually uses 224x224, but 128x128 is faster for CPU training
data_transforms = transforms.Compose([
    transforms.Resize((224, 224)), 
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

def load_data():
    full_dataset = datasets.ImageFolder(root=DATA_DIR, transform=data_transforms)
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_data, val_data = random_split(full_dataset, [train_size, val_size])
    
    train_loader = DataLoader(train_data, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_data, batch_size=BATCH_SIZE, shuffle=False)
    return train_loader, val_loader, len(full_dataset.classes)

# --- 2. EFFICIENTNET_B0 WITH TRANSFER LEARNING ---
def build_model(num_classes):
    # Load pre-trained EfficientNet_B0
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    
    # Freeze all original layers (prevents CPU from doing heavy weight updates)
    for param in model.parameters():
        param.requires_grad = False
        
    # Replace the final classification head
    # EfficientNet_B0 has 1280 input features in the last layer
    model.classifier[1] = nn.Linear(1280, num_classes)
    
    return model.to(DEVICE)

# --- 3. TRAINING LOOP ---
def train_and_validate():
    train_loader, val_loader, num_classes = load_data()
    model = build_model(num_classes)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.classifier.parameters(), lr=LEARNING_RATE)
    
    history = {'train_loss': [], 'train_acc': [], 'val_loss': [], 'val_acc': []}

    print(f"Starting training on CPU... (Classes: {num_classes})")
    
    for epoch in range(EPOCHS):
        model.train()
        t_loss, t_correct, t_total = 0, 0, 0
        
        for images, labels in train_loader:
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            t_loss += loss.item()
            _, pred = torch.max(outputs, 1)
            t_total += labels.size(0)
            t_correct += (pred == labels).sum().item()

        # Validation
        model.eval()
        v_loss, v_correct, v_total = 0, 0, 0
        with torch.no_grad():
            for images, labels in val_loader:
                outputs = model(images)
                loss = criterion(outputs, labels)
                v_loss += loss.item()
                _, pred = torch.max(outputs, 1)
                v_total += labels.size(0)
                v_correct += (pred == labels).sum().item()

        # Record metrics
        history['train_loss'].append(t_loss/len(train_loader))
        history['train_acc'].append(100 * t_correct / t_total)
        history['val_loss'].append(v_loss/len(val_loader))
        history['val_acc'].append(100 * v_correct / v_total)
        
        print(f"Epoch {epoch+1}: Train Acc: {history['train_acc'][-1]:.2f}% | Val Acc: {history['val_acc'][-1]:.2f}%")

    return history

# --- 4. REPORT & VISUALIZATION ---
def report_results(h):
    print("\n--- Final Report ---")
    print(f"Final Training Accuracy: {h['train_acc'][-1]:.2f}%")
    print(f"Final Validation Accuracy: {h['val_acc'][-1]:.2f}%")

    plt.figure(figsize=(10, 4))
    plt.plot(h['train_loss'], label='Train Loss')
    plt.plot(h['val_loss'], label='Val Loss')
    plt.title('Loss Curve (EfficientNet_B0)')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()
    plt.show()

#Run the process
hist = train_and_validate()
report_results(hist)
